# FocalTech MOH image format and layout investigation

Status: **static Windows driver analysis plus user-reported physical results** on 11 October 2026. No stored biometric samples in this repository. These are hypotheses, not a validated biometric matcher.

## Why the initial fingerprint correlations are poor

Three private raw captures from the physical 2808:5955 reader were made in A–B–A order at 13:24:17, 13:25:25, and 13:26:45. The big-endian PNGs are recognisably patterned; the little-endian PNGs show repeating row lines. In the original 80 × 64 interpretation and a ±6-pixel shift search, the measured correlations were:

| Pair | Correlation | Shift |
| --- | ---: | --- |
| A1–A2, same-finger hypothesis | +0.132 | (-2, -6) |
| A1–B, different-finger control | +0.078 | (-3, +1) |
| A2–B, different-finger control | +0.130 | (-4, -4) |

Repeating with ±12 pixels gave **+0.132, +0.100 and +0.130**, respectively. The same-finger margin over the strongest different-finger pair stayed **+0.003**. Increasing the alignment window did not solve the problem; no useful biometric separation has yet been demonstrated.

## New driver finding: sensor-specific processing assumes a 64-sample stride

The matching **MOH Windows** `FtWbioDriverUmdfV3.dll` (5.10.66.6611) was independently inspected in local disassembly, without distributing the proprietary binary.

- `CBiometricDevice::ff_sc_GetImage` at `0x180006B74` receives `width × height` positions and requests `2 × width × height` bytes via helper `0x18000793C`.
- Its general image converter at `0x180005C78` calls preprocessing helper **`0x180006184`** before normalising samples. This path is selected on our physical 80 × 64 sensor (the distinct 152 × 40 conversion path is not selected).
- The helper `0x180006184` uses a **128-byte row stride** (`0x80`, i.e., **64 16-bit samples per row**) in neighbour/edge-correction operations, with offsets extending to **80 rows**, including a pointer to row 40 at offset `0x1400` (5,120 bytes = 40 × 128). This strongly suggests the 5,120-sample intermediate buffer is internally treated as a **64 × 80 array**, even though the device's metadata returned width 80 and height 64.
- Later in the general conversion code, `0x180005C78` also performs **16-bit signed operations, sample negation, range estimation and histogram-based contrast adjustment**. Consequently our generic 1st/99th-percentile normalisation is not equivalent to the Windows processing.

**Important caveat:** hard-coded correction dimensions are evidence of how this Windows helper *indexes the intermediate sample buffer*, not proof of the physical sensor orientation, packet sample ordering, or the final image display geometry. The helper mutates its input and may map the data during conversion. The big-endian visual advantage is observational, not independent format validation.

## Next local-only layout A/B experiment

Both tools retain big-endian as the default hypothesis; **no capture or sensor writes are involved**.

```bash
cd ~/Projects/focaltech-5955-linux
git pull --ff-only

# Compare the same three captures using both arrangements,
# at the original +/-6 pixel search radius.
.venv/bin/python tools/fingerprint_compare.py --latest-three --both-layouts

# Render an alternate 64x80 preview of the first capture, in the private directory.
.venv/bin/python tools/raw_to_png.py \
  local-data/fingerprint_11-10-2026_13-24-17.raw \
  --order big --layout 64x80
```

The alternative PNG is named like `fingerprint_11-10-2026_13-24-17-big-64x80-preview.png`, at **512 × 640** pixels using the default 8× nearest-neighbour enlargement. Original 80 × 64 PNGs are not modified or overwritten.

Compare the *three correlations* for both layouts rather than selecting whichever yields the largest same-finger number; alignment searches can also boost scores from different fingers. A layout that visibly renders more coherent ridge detail and also separates independent same-finger and different-finger examples would be more promising, but three captures cannot establish biometric reliability.

Do not share the raw fingerprint files or images, create persistent templates, or enable KDE/PAM authentication at this stage.

## Corrected visual interpretation of 64 × 80 example — 11 October 2026

The device owner clarified that **the black wiggly lines in the shared edited image were manually drawn**, while **the grey areas came from the FocalTech output**. Earlier notes incorrectly attributed the black curved lines to sensor ridges. **That interpretation is withdrawn.** The manually added marks are not evidence of fingerprint ridges, boundaries or minutiae and must not be used to infer image layout or capture quality.

The unedited grey sensor content remains inconclusive: visible greyscale variation is not sufficient to establish a real fingerprint pattern or the correctness of either the 80 × 64 or 64 × 80 arrangement. The black lines are a user annotation and the edited file must not be included in quantitative image analysis.

The image itself is **not stored or linked in GitHub**. The next useful tests are entirely local: first compare the original three unedited raw captures in both layouts using `tools/fingerprint_compare.py --latest-three --both-layouts`; then investigate the Windows DLL's signed-sample correction, row ordering, normalisation and histogram operations before claiming viable fingerprint recognition. No authentication or thresholds should be enabled.

## Signed 16-bit diagnostic from four real captures — 11 October 2026

The user ran `tools/raw_sample_diagnostics.py --latest-four` on private A1, A2, B1 and B2 captures. **No raw fingerprint image or biometric sample content was shared or committed.** Only aggregate statistics are recorded here:

| Capture | Big-endian % signed-negative | Little-endian % signed-negative | Little-endian 99th percentile |
| --- | ---: | ---: | ---: |
| A1 | 42.1% | **0.0%** | 1,660 |
| A2 | 51.2% | **0.0%** | 1,616 |
| B1 | 38.9% | **0.0%** | 2,008 |
| B2 | 47.6% | **0.0%** | 1,796 |

In little-endian decoding, the four sample medians were 1,132, 1,232, 1,420 and 1,368. Big-endian interpretations had 99th percentiles around 64,515, with about 39–51% of samples interpreted as signed-negative; applying the Windows negative clamp to those byte-swapped values would erase about half the data. In little-endian interpretation, the Windows-style negative clamp changes **no** samples. Most little-endian sensor values fit an approximately **11-bit positive intensity range** (0–2047), although the exact ADC bit depth and any outliers are **unverified**. The sensible low-range distribution is **strong evidence favouring little-endian raw WORDs**, independent of the misleading visual appearance of the earlier big-endian previews.

Further static inspection of `FtWbioDriverUmdfV3.dll` general converter at `0x180005C78` confirmed that it calls a correction routine at `0x180006184`, which starts with a signed-word negativity check and zero clamp (`cmp WORD PTR ...; jge`), then makes additional data-dependent corrections. The later steps negate each 16-bit word and use signed minimum/range/histogram transforms. Reproducing only the clamp **is not the complete Windows correction pipeline**.

### Next private rendering experiment

[`tools/raw_decode_preview.py`](../tools/raw_decode_preview.py) decodes little-endian 16-bit words and generates previews for both the **80 × 64** metadata layout and experimental **64 × 80** intermediate memory layout. For each, it privately outputs:

1. **`signed-clamped`** — negative signed input values clamped to zero, then display contrast stretched over positive foreground measurements.
2. **`row-normalised-EXPERIMENTAL`** — identical starting data, with a per-row median offset removed for populated rows. This is a *diagnostic stripe-removal hypothesis*, **not** an assertion of Windows-driver behaviour; it can suppress real detail or produce misleading patterns.

Original raw files are never modified. No USB request, biometric template, authentication, network upload or GitHub image commit occurs.

```bash
cd ~/Projects/focaltech-5955-linux
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/raw_decode_preview.py \
    local-data/fingerprint_11-10-2026_14-24-20_A1.raw
```

The command writes four **private PNG previews** into ignored `local-data/` (two processing variants × two layouts, each 8× enlarged), with distinct filenames and no overwrite. Compare which images show coherent structures rather than artificial stripes. The next matching experiment should use the little-endian inputs and must evaluate both genuine and different-finger pairs, rather than picking a threshold from one comparison.

