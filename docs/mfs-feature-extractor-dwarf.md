# FtGetMfsFeatures: verified native ELF feature extractor reconnaissance

Research: 11 October 2026. Sources:

- Third-party comparison: https://github.com/scamiran149/libfprint_focaltechc652 (README, focaltech_sift_matcher.cpp, focaltech_c652.cpp).
- User-provided original native FocalTech Ubuntu package, dated 2025-02-19, **not committed**: `libfprint-2-2_1.94.4+tod1-0ubuntu1~22.04.2_amd64_20250219.deb`.
- The extracted, **unstripped** Linux ELF has build ID `62fa37ea38c700338cef64f46136ccadf7f078b1`; function addresses below are offsets specific to THIS build.

**All inspection was offline**, using ELF symbol tables, DWARF and read-only disassembly. No vendor library was executed in this investigation, no USB/fingerprint scan was used, and no biometric images or proprietary binaries are in this document.

## What the c652 repository really demonstrates

Its README mentions `FtGetMfsFeatures`, `FtGetMfbFeatures`, `FtVerifyTwoTemplate` and RANSAC. Its **actual** open-source matcher, however, substitutes **OpenCV SIFT**:

- 64x80 input upscaled 10x; bilateral smoothing, box-filter background subtraction, min-max grayscale stretching, and CLAHE.
- Standard `cv::SIFT::create()`, brute-force KNN, Lowe ratio filter 0.8, `findHomography(..., RANSAC, 5.0)`.
- Five enrolment impressions, score = maximum RANSAC inlier count across stored impressions, hardcoded verification threshold = 13.

These are the third-party author's engineering choices, **not reverse-engineered FocalTech extractor code or validated parameters**. Their exact USB product is `2808:c652`, not `2808:5955`; do not install, adapt commands for or change USB ID tables on our reader.

**Descriptor storage defect in the c652 prototype:** OpenCV SIFT descriptor rows in `CV_32F` contain **128 float32 entries = 512 bytes per feature**. The serializer in `focaltech_sift_matcher.cpp` instead reads the row pointer as `uint8_t*` and copies **only 128 bytes**, then the deserializer interprets these as 128 unsigned integer values and casts them to floats. The original 128-element float vector cannot round-trip. Thus the c652 reference's serialized enrolment cannot be relied on without correction and independent verification. This defect does not tell us FocalTech's native template format.

Our earlier local `tools/sift_compare.py` baseline, using actual but private A1/A2/B1/B2 impressions, showed **5–6 RANSAC inliers in both genuine and different-finger pairs** under 64x80. Generic SIFT+homography presently fails to separate them. Do not assume upscaling from 64x80 creates biometric information or that 13 inliers is a safe matching threshold.

## Direct static evidence from FtGetMfsFeatures

ELF local symbol `FtGetMfsFeatures` starts at file-relative VMA `0xe0450`. Inspection of calls **within its disassembled body** confirms:

1. `FtCreateInitImg`: input preparation.
2. `FtBuildGaussPyr` at `0xdd250`: Gaussian scale-space.
3. `FtBuildDogPyr` at `0xdd730`: difference-of-Gaussians.
4. `FtScaleSpaceExtrema` at `0xdbb80`: scale-space extrema extraction.
5. `FtMfsCalcGradMagOri` at `0xddd10` and `FtDominantOri`/`FtSmoothOriHist`: orientation assignment.
6. `FtComputeDescriptors` at `0xde190`: feature description.

This **confirms a scale-space / DoG / orientation / descriptor design**, not standard OpenCV-SIFT equivalence. The ELF also contains `FtGetMfbFeatures` (0xe25f0), `FtMfbDescriptors` (0xdf8c0), `FtFeatureCmp` (0xdb850), and `FtCalcBinFeature` (0x11d510). Their exact relationships and parameter values are not yet mapped.

## Actual DWARF type evidence (not source code)

DWARF gives the signature at `0xe0450` as a function returning `ST_EXTREMUM_NUM` with arguments:

- `inPara`: `ST_InputForTemplate` (the observed type occupies 72 bytes).
- `feat1`, `feat2`: pointers to `ST_Feature`.

In this build, `ST_EXTREMUM_NUM` is an 8-byte structure consisting of two signed 32-bit extrema counters, `nMaxExtremum` and `nMinExtremum`.

A `ST_Feature` record is **44 bytes** in the DWARF layout:

| Byte offset | Field | Interpreted DWARF type |
| ---: | --- | --- |
| 0 | `x` | float32 |
| 4 | `y` | float32 |
| 8 | `ori` | float32 |
| 12 | `bDescri[8]` | 8 x uint32 (32 bytes, 256 bits) |

The field name `bDescri` and 256-bit representation are **consistent with a compact binary descriptor**. However, it is not yet established whether this is the **only** representation, a derived feature, which mode produces it, how the 256 bits are generated, or how feature counts and template layouts relate.

The 72-byte `ST_InputForTemplate` parameter holds at least these type-and-offset facts:

| Offset | Field | Type |
| ---: | --- | --- |
| 0 | `intvls` | int32 |
| 4 | `sigma` | float32 |
| 8 | `contrThr` | float32 |
| 12 | `curvThr` | int32 |
| 16 | `imgDbl` | int32 |
| 20 | `descrWidth` | int32 |
| 24 | `descrHistBins` | int32 |
| 32 | `img` | pointer to image structure |
| 40 | `octave` | uint8 |
| 41 | `validArea` | uint8 |
| 48 | `validFlg` | uint8 |
| 56 | `badPixselValidFlg` | uint8 |
| 64 | `isFT9391` | uint8 |
| 65 | `algType` | uint8 |
| 66 | `sensorCol` | uint8 |
| 67 | `isSpeedUp` | uint8 |
| 68 | `imgScale` | float32 |

These are binary layout observations, not reproduced proprietary C source. Field names alone **do not reveal default values or matching semantics**.

## Implications for our 2808:5955 project

The third-party README provided a good clue, but the **unstripped vendor binary is the stronger evidence**. In particular, blindly following the c652 SIFT/RANSAC pipeline would discard potentially critical proprietary details (descriptor structure, input masks, valid-area flags, image-scaling mode, feature counts, additional matching scores, multi-impression templates).

**Best next offline analysis:** trace which caller populates `ST_InputForTemplate` and its `descrWidth/descrHistBins/contrThr/sigma` fields, and establish how `FtComputeDescriptors` and `FtCalcBinFeature` populate `bDescri[8]` for synthetic inputs. Begin with statically verified values and independently authored C code, then validate synthetic output against the isolated Linux reference function only if a safe non-USB call boundary is established.

No new physical captures are currently required. Do not copy c652 USB commands or install any other driver. Keep A1/A2/B1/B2 scans and future biometric templates private in ignored `local-data/`; no real biometric data or descriptor vectors should enter public GitHub.
