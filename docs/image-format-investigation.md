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

## First visual inspection of alternate 64 × 80 image — 11 October 2026

The device owner tested the new `--order big --layout 64x80` option and shared a **manually edited** example solely for private visual discussion. In this alternate row-major arrangement, a **curved upper boundary and several approximately parallel, ridge-like arcs** are more apparent. The lower part remains poorly resolved / noisy. The inspected edited PNG was 64 × 80 pixels; its edit history and contrast settings are unknown, so the displayed grayscale levels cannot be attributed directly to the sensor.

**Interpretation:** This qualitatively supports investigating the 64 × 80 intermediate-memory layout inferred from the Windows DLL's 128-byte stride, but it does **not** establish that the raw sensor produces genuine ridge/minutiae detail, prove correct endian/order/polarity, or verify fingerprint matching. The edited image is **not stored or linked in GitHub**.

Next priority: compare the **unchanged original raw files** under both layouts using `tools/fingerprint_compare.py --latest-three --both-layouts`, ensuring all A1/A2, A1/B, A2/B scores are evaluated. Assess unedited imagery privately before any new preprocessing and never treat a similarity score as a login decision.
