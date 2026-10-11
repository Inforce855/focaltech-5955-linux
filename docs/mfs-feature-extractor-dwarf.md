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

**Best next offline analysis:** trace which caller populates `ST_InputForTemplate` and its `descrWidth/descrHistBins/contrThr/sigma` fields, then determine which `FtComputeDescriptors` branch is used for our sensor mode and how the gradient histogram is constructed. `FtCalcBinFeature` appears to belong to a **separate image/minutiae assessment path**, not the routine writing `ST_Feature.bDescri[8]`. Begin with statically verified values and independently authored C code, then validate synthetic output against the isolated Linux reference function only if a safe non-USB call boundary is established.

No new physical captures are currently required. Do not copy c652 USB commands or install any other driver. Keep A1/A2/B1/B2 scans and future biometric templates private in ignored `local-data/`; no real biometric data or descriptor vectors should enter public GitHub.

## Descriptor bit-packing breakthrough: direct `FtComputeDescriptors` disassembly

Static disassembly of the **2025 Ubuntu FT9362 ELF**, no vendor execution,
shows a specific binary descriptor writer within `FtComputeDescriptors`
at offsets **`0xdf320`–`0xdf511`**. It first zeroes all eight 32-bit
words of `ST_Feature.bDescri` at output offsets +12 through +43.

1. The internal descriptor histogram is organised as **two groups of
   eight spatial cells × eight orientation bins** (128 float32 values).
2. For each orientation and group, the code accumulates eight cell values,
   then multiplies by **0.125f** (stored at `0x193740`, confirmed via ELF
   read-only data). An individual histogram value **greater than or equal
   to** that orientation's eight-cell average sets one bit. This generates
   the **first 128 bits**.
3. An adjacent-cell comparison with **1.05f** (read-only data `0x193744`)
   generates a further **128 bits**, including wrapping cell 0 against
   cell 7. Bit writes use `1 << position` and OR into
   `bDescri[bit_index/32]`, least-significant bit first.

These findings show that the **256-bit fingerprint feature descriptor
is constructed by quantising orientation-histogram relationships**;
it is not an AES-256 encryption key. This conclusion applies to this
particular code path, not necessarily every vendor algorithm mode.

The independently written C module `native/ft_descriptor_pack.c`
implements this confirmed packing stage for synthetic histogram inputs;
five synthetic tests passed under strict GCC plus ASan/UBSan.
**No vendor byte-output reference is yet available for this extractor**.
We have not reconstructed the gradient/orientation histogram input to
this stage, feature detection, descriptor matching or enrollment.
These C features are not suitable for identity decisions.

## 8×8×8 upstream histogram: confirming the missing link

Further direct disassembly of the original unstripped Ubuntu ELF:

- At `0xde233`–`0xde249`, `FtComputeDescriptors` allocates a float
  histogram of `descrWidth² * descrHistBins` entries. An 8×8×8 mode
  therefore uses **512 floats**, rather than the 128 comparisons
  in one specific output-packing branch.
- At `0xde43b`–`0xdeae1`, the descriptor samples a neighbourhood
  covering offsets `-15..15` along two axes in the relevant mode,
  obtains gradient magnitude/orientation using
  `FtMfsCalcGradMagOri` (call at `0xde6d3`), subtracts the keypoint
  angle, circularly wraps angles, and performs trilinear interpolation
  between spatial cells and 8 orientation bins.
- The original ELF contains a precomputed `GAUSS_WEIGHT_TAB` and the
  orientation scale constant `0x19373c = 1.27323949f ≈ 8/(2π)`.
  Its exact scale-specific Gaussian table, intermediate feature
  selection and algorithm-mode flags are still unresolved.

**Correction to earlier shorthand:** `ST_Feature.bDescri[8]` is
256 *bits of final descriptor*, not a 256-value gradient histogram.
The experimental 128-value array in `ft_descriptor_pack.c` models a
specific comparison branch but cannot simply be identified with the
complete upstream histogram. A validated 512→packed-bit transformation
still needs to be reconstructed and tested against original vendor output.

`native/ft_mfs_histogram.c` now implements a **separate independent
research approximation** for 8×8×8 sampling from synthetic gradients.
Its Gaussian σ and cell width are model choices, not vendor constants.
Six local tests passed under strict compiler flags and sanitizers.
Do not use its outputs for fingerprint verification.

## Another unstripped FT9366 library: exact Gaussian scale evidence

The operator uploaded a separate **7,600,216-byte proprietary libfprint ELF**
(`libfprint-2.so.2.0.0`, SHA-256 `db95bcdf068c63a16d6fe37a55238d1dafcbe9e4d61387b2cf0bd4a631712cf4`,
Build ID `950524d26b0581f5b384b7ac4cadf6afccb6b0f9`). This is the EXACT same
Git blob (`f2555e82f06cb411a5b2b580eb6b2e91d9a4365d`) listed in
[leopalladium/focaltech-ft9366-arch-shim](https://github.com/leopalladium/focaltech-ft9366-arch-shim).
It is **not** the previous 2025 Ubuntu ELF (7,309,376 bytes, Build ID
`62fa37ea38c700338cef64f46136ccadf7f078b1`). Both are unstripped and
contain DWARF debug information. Neither binary was installed or executed.

### Machine-code and DWARF comparison

- The new binary contains `FtComputeDescriptors` at `0xd66b0` (size
  `0x1724`) and `FtGetMfsFeatures` at `0xd8970` (size `0x219d`). The older
  Ubuntu ELF has the same named functions and **identical code lengths**
  at `0xde190` and `0xe0450` respectively. This supports reuse of the
  same feature-extractor implementation, but is not a proof of identical
  outputs in every device mode.
- The new ELF includes a distinct FT9366 image processing path named
  `fw9366_histNormalize` at `0x1621d5`, in addition to the separate
  `ft9362_histNormalize` at `0x47a30`. Do not assume that either one
  is correct for hardware `2808:5955`.
- Its old `libgusb.so.2` version references include
  `LIBGUSB_0.1.0`, `0.2.2`, `0.2.4`, `0.3.3`.
  That supports the need for caution on modern systems; it does
  not by itself isolate the precise loader/runtime incompatibility.
- Crucially, DWARF explicitly types `GAUSS_WEIGHT_TAB` as a
  **float32 `[3][256]`** array, address `0x211ac0` and size `0xc00`.
  The assembly in `FtComputeDescriptors` selects a 1024-byte block
  via `(selected_level - 1) << 10`, then looks up a float inside.
  Treating each block as a 16×16 grid is strongly supported by
  its symmetric radial values and the descriptor's ±15 patch.
- **The entire 3,072-byte Gaussian table is byte-identical across both
  binaries** (SHA-256 of table only:
  `04f9417216982cffd9847e2eb70da83c082167fc91760e7fba347c64a4c1ccfd`).
  All three blocks have 256 nonzero float values, with a radial profile.
- The independently derived Gaussian model
  `w(x,y,level) ≈ exp(-(x²+y²)/(2σ²))` with
  `σ(level) = 19.2 × 2^((level-3)/3)` for levels 1..3 yields
  approximate `σ = 12.095242, 15.239050, 19.200000`.
  Compared across **all 768 vendor table values**, maximum absolute
  difference was **less than 5.5e-7** for that model. This is a
  numerical fit, *not* a byte-for-byte bit-level reproduction of
  the table's float rounding.
- DWARF additionally contains a `GAUSS_WEIGHT_TAB2` declaration
  of float32 `[3][1369]` (`1369 = 37²`) stored as debug constants.
  Its relationship to runtime selection is not yet confirmed; do not
  assume this larger table is active for the user's device.

### Practical impact

The original experimental histogram code uses **a guessed Gaussian
width `σ = 8`**. We now have vendor-grounded evidence for three
scale-dependent widths; that original approximation can be replaced
or supplemented using **independently generated Gaussian weights**
without redistributing the proprietary lookup table. First establish
how `selected_level`, input scaling, rotated offsets and validity
masks reach `FtComputeDescriptors`; then use synthetic-only tests.
All real fingerprint scans and proprietary binaries stay out of GitHub.
