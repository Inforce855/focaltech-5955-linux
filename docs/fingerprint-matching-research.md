# Private fingerprint image similarity experiments

Date: 11 October 2026. Status: **experimental offline image comparison, NOT an authentication driver**.

## Physical reader findings

The FocalTech 2808:5955 sensor reports an image geometry of **80 × 64** pixels, with **10,240 bytes** of intermediate sample data in captures. The owner successfully produced three image files from finger A, finger B and finger A again. The first and third look similar; the second visually differs. The owner's big-endian PNG previews show more recognisable pattern than the little-endian previews, which show repeated lines. These impressions are **not independent proof of fingerprint ridge structure, correct endianness or identity matching**.

## Offline comparison prototype

[`tools/fingerprint_compare.py`](../tools/fingerprint_compare.py) accepts exactly three original `.raw` files in **A1, B, A2** order. It:

1. Decodes 16-bit samples using big-endian by default; this is a working hypothesis.
2. Clips intensities to the 1st/99th percentile, rescaling to a common contrast range.
3. Subtracts an 11×11 box-filtered background from a 3×3 locally averaged image, emphasising spatial detail while suppressing broad lighting patterns.
4. Searches x/y translation within ±6 pixels and takes the largest overlap-normalised Pearson correlation on a central region.
5. Reports the A1-vs-A2 score alongside A1-vs-B and A2-vs-B controls, shifts, and a margin over the strongest control. No threshold is used to declare biometric verification success.

Only basic scores and capture basenames are printed, never raw samples, templates or pixel values. The application performs **no USB I/O or filesystem writes** and never enables `fprintd`/PAM/KDE fingerprint login. The ten unit tests use wholly synthetic signals to check translation recovery, brightness robustness, pair ranking, file-size validation, low-detail rejection, and byte-order distinctions.

## Run on the owner's computer

```bash
cd ~/Projects/focaltech-5955-linux
git pull --ff-only

# Most recent three captures, assuming they are A then B then A:
.venv/bin/python tools/fingerprint_compare.py --latest-three

# Or explicitly select capture filenames in A/B/A sequence:
.venv/bin/python tools/fingerprint_compare.py \
    local-data/FIRST.raw local-data/SECOND.raw local-data/THIRD.raw

# Run synthetic offline regression suite:
.venv/bin/python -m unittest discover -s tests -v
```

## Limitations and evaluation requirements

- A correlation ranking from **one A–B–A trial** does not establish biometric identity, liveness or security. Static sensor patterns, changing contact pressure, rotation, finger motion and data conversion errors can all produce misleading results.
- At **80 × 64** pixels this is a very small image, and standard minutiae detection might not extract stable characteristics. Compare more independent same-finger and different-finger captures before assessing any matching approach.
- This first prototype corrects only **translation**, not rotation or non-rigid distortion. Alignment may choose a misleading local maximum when image patterns are repetitive.
- Avoid creating a real-access/denied security decision or configuring login, sudo or screen unlock from an unvalidated score.
- Fingerprints cannot be changed like passwords; keep `.raw`, templates and PNGs in the local ignored private directory, with limited file permissions. Never publish them in repository commits or issues.

Next: obtain actual A–B–A scores from the real sensor privately; compare different capture conditions. Depending on results, study the matching Windows DLL's image conversion and the current `libfprint` image processing/matching pipeline. Do not introduce a security decision until robust enrolment, repeatability and independent impostor testing exist.

## First physical A–B–A scores — 11 October 2026

The owner ran the existing offline, big-endian comparator against three real private captures made at 13:24:17 (A1), 13:25:25 (B), and 13:26:45 (A2), with the default ±6-pixel translation search. The raw images remain local and were not uploaded.

| Pair | Best correlation | Shift (x, y) | Overlap |
| --- | ---: | ---: | ---: |
| A1 vs A2, same-finger hypothesis | +0.132 | (-2, -6) | 3,036 px |
| A1 vs B, different-finger control | +0.078 | (-3, +1) | 3,315 px |
| A2 vs B, different-finger control | +0.130 | (-4, -4) | 3,072 px |

The same-finger pair barely ranks first: its advantage over the strongest different-finger comparison is only about **+0.003**. That is **not meaningful discrimination** and certainly not enough to configure an authentication threshold. The A1→A2 best shift ends at `y=-6`, precisely the existing search boundary. This could reflect larger translation or accidental boundary maximisation; it is not proof of any image registration fix.

The **next no-new-capture diagnostic** is to run `--max-shift 8` using the exact same private files, and report **all three pair scores** rather than focusing only on A1–A2. Larger search windows can raise impostor scores as well. Longer term the preprocessing and sample orientation, nonrigid finger placement and static sensor artefacts need to be examined locally. Do not declare identity matches based on this trial.

## Live four-capture A1/A2/B1/B2 results — 11 October 2026, 14:24 BST

User tested the new manually triggered four-shot session successfully on the actual reader. The four private files were captured **14:24:20 A1, 14:24:24 A2, 14:24:37 B1, 14:24:42 B2**, so the session interface and private file labels worked.

Offline comparator used **big-endian, 80 × 64, ±6 pixel translation**:

| Pair | Correlation | Shift |
| --- | ---: | --- |
| A1 vs A2 (same A) | +0.089 | (-6, +5) |
| B1 vs B2 (same B) | +0.081 | (+1, -6) |
| A1 vs B1 (different) | **+0.118** | (+2, +6) |
| A1 vs B2 (different) | +0.088 | (+0, -6) |
| A2 vs B1 (different) | +0.081 | (+0, +1) |
| A2 vs B2 (different) | +0.088 | (+1, -4) |

The strongest cross-finger score (+0.118) is higher than **both** same-finger scores. Genuine A is 0.029 *lower* than the highest cross-finger score, and genuine B is 0.037 lower. Several optimal alignments are on the imposed ±6 search boundary. **No reliable matching/discrimination was demonstrated.** Increasing the translation window did not help the earlier A–B–A experiment; focus on correct signed-sample processing and sensor-specific correction before tuning a threshold or increasing shifts.

The Windows MOH general image converter at VA `0x180005C78` calls correction routine `0x180006184`, which explicitly checks **signed 16-bit values** (`cmp word ...; jge`) and sets negative input samples to zero before sensor correction, then negates 16-bit samples and performs signed min/range and histogram-based output mapping. The current raw converter interprets bytes as **unsigned** `H` values, in either endian order, before percentile-stretching. These are **not equivalent processing paths**, potentially explaining the noisy images and weak correlation scores. The exact correction routine is not yet fully reproduced; resist premature identity claims.

No biometric files or edited images have been committed to GitHub.


## Four-capture test: little-endian, 64 × 80, ±12-pixel search (11 October 2026)

The same four private samples used for the earlier big-endian comparisons were compared again, now interpreted as **little-endian 16-bit** with experimental **64 × 80** row-major layout and a ±12-pixel search. The user reported only numerical scores and metadata; **no real fingerprint image, raw sample, or template was committed or shared with the repository**.

| Pair | Correlation | Shift | Overlap pixels |
| --- | ---: | --- | ---: |
| A1 vs A2 (same finger A) | **+0.323** | (+12, +8) | 2,400 |
| B1 vs B2 (same finger B) | +0.210 | (-3, -8) | 2,940 |
| A1 vs B1 (different) | +0.212 | (-12, -1) | 2,680 |
| A1 vs B2 (different) | +0.206 | (-12, -9) | 2,360 |
| A2 vs B1 (different) | +0.221 | (-12, +7) | 2,440 |
| A2 vs B2 (different) | +0.253 | (+10, -8) | 2,520 |

The strongest different-finger control was +0.253. Thus the margins were **+0.070** for finger A and **−0.043** for finger B. Finger A appears more consistent but finger B still does not separate from impostor controls, and **no secure verification is supported**.

**Critical confound:** these scores cannot be compared directly against the preceding big-endian experiment (+0.089/+0.081), which used both a different byte order and a narrower **±6-pixel** alignment window. The apparent increase could reflect more coherent low-bit-depth data, alignment search overfitting, altered preprocessing, or a combination. Multiple pairs hit the ±12 boundary, and the best same-finger alignment used only **2,400 overlapping pixels**; taking the highest correlation across many offsets can inflate scores for unrelated fingers.

**Next controlled test:** run exactly the same four raw files with **little-endian, both 80 × 64 and 64 × 80 layouts, and the original ±6-pixel search**, keeping all other processing constant:

```bash
.venv/bin/python tools/fingerprint_compare.py --latest-four --order little --both-layouts --max-shift 6
```

Examine all six scores for each layout. Do not tune authentication thresholds or publish real fingerprint images; any future demo art must be wholly synthetic.


## Controlled geometry comparison — same four little-endian captures, ±6 pixels (11 October 2026)

The user reran the exact same private A1/A2/B1/B2 samples, keeping byte order (**little-endian**), correlation method and translation search (±6 pixels) constant, and comparing both tested image layouts. **No biometric files or sample values were uploaded or committed.**

| Comparison | 80 × 64 r | 80 × 64 shift | 64 × 80 r | 64 × 80 shift |
| --- | ---: | --- | ---: | --- |
| A1–A2 (same finger A) | **+0.491** | (-2, -6) | +0.157 | (-6, -6) |
| B1–B2 (same finger B) | +0.176 | (-1, +4) | +0.190 | (-1, +5) |
| A1–B1 (different) | +0.161 | (-6, +1) | +0.173 | (-6, -2) |
| A1–B2 (different) | +0.288 | (+0, +4) | +0.141 | (-4, +5) |
| A2–B1 (different) | +0.128 | (+2, -4) | +0.109 | (-6, +6) |
| A2–B2 (different) | +0.138 | (+2, -6) | +0.130 | (+6, -6) |

Under **80 × 64**, strongest cross-finger score is **+0.288**: A's genuine margin is **+0.203** (tool prints +0.204 because of unrounded underlying values), B's genuine margin is **−0.112** (tool prints −0.111). Under **64 × 80**, strongest cross-finger score is **+0.173**: genuine margins approximately **−0.016** (A) and **+0.017** (B).

Interpretation: **little-endian 80 × 64 is the leading experimental format**; the sensor itself reported width 80 and height 64. The A repeat pair has substantially higher correlation than all control comparisons in that layout, and the user independently reported visible shifted structure in A1/A2. However **finger B is still less similar to itself than one unrelated-finger pairing**, so no reliable recognition threshold, biometric identification, or deployment claim can be made.

The A1/A2 80 × 64 optimum again reaches **y=-6**, the search boundary; this warrants a finger-placement/coverage investigation, **not** simply increasing the search limit, which inflates different-finger maxima too. The greater consistency of A versus B could reflect position/pressure, poor capture quality, rotation, finger anatomy, sensor artefacts or incorrect correction. These four samples do not discriminate among explanations.

**Recommended next controlled hardware test:** run one more four-capture Enter-triggered session, but **reverse which actual finger is assigned to the two roles**: place former *finger B* twice in the A1/A2 slots, then former *finger A* twice in B1/B2 slots. Compare with **`--latest-four --order little --layout 80x64 --max-shift 6`**. This checks whether the difficulty follows the particular finger or the capture position/order. Results are exploratory and local-only. Do not publish fingerprint images or use for login.
