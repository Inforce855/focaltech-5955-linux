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
