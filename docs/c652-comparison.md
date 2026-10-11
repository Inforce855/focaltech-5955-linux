# FocalTech 2808:c652 open-source prototype comparison

Source: https://github.com/scamiran149/libfprint_focaltechc652
Inspected: 11 October 2026. The reference is a different USB product, and does not demonstrate compatibility with 2808:5955.

## Verified overlap

| Component | 2808:c652 reference | Our tested 2808:5955 |
| --- | --- | --- |
| Endpoints | OUT 0x01; IN 0x82 | OUT 0x01; IN 0x82 |
| Frame commands | 02 00 LEN CMD PAYLOAD BCC XOR | Same on validated requests |
| Image command | 0x81 | 0x81 works |
| Image reply | 10246 bytes, pixels starting at offset 4 | 10246 bytes with checksummed 10240-byte payload |
| Image words | Little-endian 16-bit | Little-endian supported by physical aggregate statistics |
| Geometry | 64 columns by 80 rows | Firmware metadata says 80 by 64; Windows correction uses 64-sample stride; actual row layout unresolved |
| Command 82 73 01 | Called capture trigger by this prototype | On our hardware, verified finger PRESENCE query: returns 05 touched, 06 absent |

The last line is a real operational difference. The c652 driver also polls 80 02 for finger presence and sends setup commands 37 01 01 01 and 80 02 01. Their meaning on our 5955 hardware has NOT been verified. Never send these commands just because they appear in another project's driver. Only the other PID 2808:c652 is in its supported USB ID table. Do NOT install this other driver, add our PID to it, replace system libfprint, or enable PAM/KDE authentication based on it.

## Image-processing lead

The reference describes an OpenCV pipeline: 10x bicubic scale, bilateral smoothing, 31-pixel box-filter background subtraction, min/max normalisation, CLAHE, SIFT feature extraction, 0.8 descriptor ratio filter, and RANSAC geometry verification. That may handle displacement/rotation better than our crude pixel correlation, but **upscaling does not generate new biometric detail**, and repeating sensor artefacts can cause false feature correspondences.

Reference files:
- https://github.com/scamiran149/libfprint_focaltechc652/blob/main/README.md
- https://github.com/scamiran149/libfprint_focaltechc652/blob/main/libfprint/drivers/focaltech_c652.cpp
- https://github.com/scamiran149/libfprint_focaltechc652/blob/main/libfprint/drivers/focaltech_sift_matcher.cpp
- https://github.com/scamiran149/libfprint_focaltechc652/blob/main/focaltech_test.py

### Important shortcomings of that prototype

1. It has a hardcoded match threshold of 13 RANSAC inliers, not validated for our 5955 device.
2. The source's SIFT descriptors are 128 float32 numbers (512 bytes) per feature, but its template SERIALIZER copies only 128 bytes from each CV_32F descriptor. Deserialization interprets those as 128 unsigned bytes, then converts to floats. That cannot round-trip the original descriptors faithfully, so stored enrollments in this reference implementation deserve scrutiny. We will not copy or rely on that template mechanism.
3. Its README calls the intensity readings 10-bit ADC, whereas our little-endian 99th percentiles were 1616–2008 (more than 1023); ADC range for the 5955 sensor is still unknown.
4. No standalone LICENSE file was present in the inspected repository tree. Our diagnostics will use independently implemented public OpenCV algorithms with attribution, not copied source.

## Latest controlled physical experiment (user-provided aggregate statistics only)

11 October 2026 second A1/A2/B1/B2 session, little endian, ±6 pixel search:

| Statistic | 80 x 64 | 64 x 80 |
| --- | ---: | ---: |
| Same finger A | 0.234 | 0.293 |
| Same finger B | 0.197 | 0.122 |
| Strongest different-finger | 0.201 | 0.151 |
| Finger A separation | +0.032 | +0.143 |
| Finger B separation | -0.004 | -0.029 |

64x80 gives a stronger A-versus-different-finger separation in this session, and corresponds to the owner's visual observation that unedited grey structures look more finger-like. B fails in either layout; neither is production-ready and the correct row mapping remains unresolved.

## Safe offline adaptation

An isolated experimental Python utility, tools/sift_compare.py, reimplements the broad publicly described OpenCV pipeline from standard algorithms and compares four private RAW captures as both layouts. It prints only keypoint counts and matching/inlier counts; it does not save images, features or templates and never uses the USB reader.

Requirements: optional opencv-python-headless installed in the repository virtual environment. Do not replace system libfprint. From project directory:

    git pull --ff-only
    .venv/bin/python -m pip install opencv-python-headless
    .venv/bin/python -m unittest discover -s tests -v
    .venv/bin/python tools/sift_compare.py --latest-four

This is not a biometric verification algorithm. Any future production implementation needs extensive genuine and impostor testing, proper enrollment/storage handling and a safe authentication fallback.

No genuine biometric samples were uploaded or committed; a future public demonstration should use clearly labelled synthetic images only.


## 11 October 2026: first four-file SIFT results on 2808:5955

User ran the isolated offline `tools/sift_compare.py --latest-four` on their private 14:55 A1/A2/B1/B2 capture set. Only aggregate statistics are recorded; **no biometric media, raw values or descriptors have been published**.

| Pair | 80 × 64 ratio matches / RANSAC inliers | 64 × 80 ratio matches / RANSAC inliers |
| --- | --- | --- |
| A1 vs A2 (same A) | 7 / 4 | 29 / 5 |
| B1 vs B2 (same B) | 7 / 4 | 44 / 6 |
| A1 vs B1 (different) | 5 / 4 | 39 / 5 |
| A1 vs B2 (different) | 10 / 4 | 45 / 6 |
| A2 vs B1 (different) | 9 / 5 | 56 / 5 |
| A2 vs B2 (different) | 11 / 4 | 53 / 6 |

Keypoint counts: 80 × 64 A1=218, A2=244, B1=147, B2=148 (average 189.25); 64 × 80 A1=2285, A2=1919, B1=1801, B2=1750 (average 1938.75). This is roughly 10.2× as many keypoints in 64 × 80, but **no genuine/impostor separation**.

A RANSAC homography may be fitted from as few as four point correspondences. Seeing 4–6 inliers in both genuine and impostor comparisons is not reliable evidence of fingerprint similarity. The reference driver's claimed 13-inlier threshold would reject all trials, although it is not validated for this PID. More keypoints could mean sensor ridge details, row-boundary artefacts, or interpolated noise.

### Next offline experiment: row-boundary statistics

The new `tools/row_boundary_probe.py` measures consecutive-sample jumps at each hypothesised 64- or 80-word line boundary compared against within-row differences and estimates vertical neighbour continuity. It runs on original little-endian samples, **before interpolation or SIFT**, printing only aggregate numerical measurements; no USB or biometrics are uploaded or written.

If a candidate width matches true physical row order, wraparound from the end of one row to the start of the next might show larger jumps than within a row. However zero-background regions, row-wise sensor calibration, internal tiling and nonuniform noise can mislead the result. Do not treat this heuristic as proof.

Run from project root:

```bash
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/row_boundary_probe.py --latest-four
```

All real fingerprint data stay in private local-data/; no image or sample values belong in GitHub.
