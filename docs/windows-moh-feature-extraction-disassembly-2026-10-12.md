# MOH 2808:5955 — Windows feature-extraction dispatch and initial parameters

**12 October 2026.** Read-only static reverse-engineering of the owner's **matching** Windows match-on-host engine; no executable or fingerprint samples are published.

- Private original: `ftWbioEngineAdapter.dll` from `7_Fingerprint-module.zip`, `MOH/FocalTechFPSSOdriver25H2x64V5.10.66.6611_WHQL`.
- SHA256 `a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c`; PE64 preferred image base `0x180000000`.
- Tool: `llvm-objdump -d --x86-asm-syntax=intel`; PE .rdata and .data bytes inspected locally; start/end function addresses from PE `.pdata` runtime-function table.
- Analysis is **offline/static**. We have not executed this DLL under Windows or Linux, traced a live call stack, decoded its complete feature template or confirmed the runtime algorithm mode on the physical reader.

## Important correction: mode 1 is MFB, not MFS

Earlier research showed that the DLL **contains** SIFT-like MFS symbols, but that alone did **not** establish the algorithm active during Windows Hello login. The actual `FtGetTemplate` feature-extraction dispatch reads the mode byte at `0x180225C51` (`movzx ecx, byte ptr [rip+...]`, `0x180036496` and `0x18003757B`) and takes one of these branches:

| Mode byte | Core extraction call within `FtGetTemplate` (0x1800354C0) | Identification grounded in nearby log strings |
| --- | --- | --- |
| `1` | `0x180036666 -> 0x1800C14F0` | `FtGetMfbFeatures` path: embedded `focaltech-lib:FtGetMfbFeatures...sigma ... intvls ... contrThr ... curvThr`, referenced at `0x1800C156D` |
| `0, 2, 3, 4` | `0x1800365D5 -> 0x1800BEB70` | `FtGetMfsFeatures` path: parameter log at `0x1800BEC08`; separately encoded `FtScaleSpaceExtrema`, `FtCalcMfsFeatureOris`, `FtComputeDescriptors_x_2` diagnostic paths |
| `5` | `0x18003661F -> 0x1800F27D0` | `FtGetMfsFeatures_v2` internal diagnostic, e.g. reference `0x1800F2921` |
| `6+` | setter clamps to `1` | `0x180033FE0..033FF4` and `0x180008CC0..008CDE` compare the byte against `6` and select `1` for out-of-range values |

**Static default:** The initial data byte at `0x180225C51` is `01` in the shipped DLL, pointing to **MFB** on an unchanged configuration. But `focal_SetAlgoMode(%d)` exists (log string `0x1801BE220`, xref `0x180001471`), the setters write this byte, and application/engine initialization can select another branch. **No runtime mode is confirmed for the successful Windows Hello login**. The second nearby template-building path at `0x180037445` also branches to MFB `0x1800C14F0` for mode 1 or MFS `0x1800BEB70` for modes below 5; the mode-5 handling there is not yet fully resolved.

### Observed initial scale-space parameters

The compiled global algorithm settings are explicitly read by the template code at `0x180036490..0364B6` and logged at `0x180035932`:

| Parameter in `gAlgInfor` | DLL address | Raw stored type/value |
| --- | --- | --- |
| `intvls` | `0x180225C30` | `int32 = 3` |
| `curvThr` | `0x180225C34` | `int32 = 15` |
| `sigma` | `0x180225C38` | `float32 = 1.6000000238` |
| `contrThr` | `0x180225C3C` | `float32 = 0.01999999955` |

The **parameter order** in the log is `intvls, sigma, contrThr, curvThr`, while the memory layout is `intvls, curvThr, sigma, contrThr`. This difference is confirmed by the assembly's register/stack argument setup. These are the **compiled initial values**, not yet runtime values from a 5955 capture. The mode-1 MFB feature routine also logs these four parameter names at `0x1800C156D`, loading the caller's parameter structure.

### MFB candidate feature pipeline (mode 1)

The active branch **if mode remains 1** is `FtGetMfbFeatures` beginning at `0x1800C14F0`.

The engine includes the following concrete read-only clues in this code region:

1. **Multiscale image preparation and extrema:** MFB feature setup at `0x1800C14F0`; calls into `0x1800C36C0` (`0x1800C18EC`), `0x1800C41B0` (`0x1800C1C01`), and `0x1800C4610` (`0x1800C1E21`). Within this same large extraction region, diagnostic string `FtScaleSpaceExtrema cost time = %d ms` is referenced at `0x1800C1E7A`. The exact roles of each helper still require an instruction-by-instruction trace.
2. **Orientation:** The adjacent MFB code block at `0x1800C20EB..0x1800C34D0` contains `FtCalcBriskFeatureOris cost time = %d ms` at xref `0x1800C2CE4`. This is direct evidence of a **BRISK-named orientation computation**, but not proof that it implements the stock OpenCV BRISK algorithm.
3. **Descriptor:** The same block references `FtMfbDescriptors_x_2 cost time = %d ms` at `0x1800C3376`. Direct calls around `0x1800C32F5` and `0x1800C3322` both target `0x1800C8990`, likely a descriptor subroutine by proximity to the diagnostic, though that callee's exact role is unverified. The descriptor's bit length, sample pairs, neighbourhood, coordinate/orientation convention and output representation remain unknown.

### MFS alternate pipeline (modes 0, 2, 3, 4)

A separate MFS extraction family is present:

- `FtGetMfsFeatures` diagnostics at `0x1800BEC08` in the function beginning `0x1800BEB70`.
- `FtScaleSpaceExtrema` time log in `0x1800BF4C6..BF71A`, xref `0x1800BF63B`.
- `FtCalcMfsFeatureOris` time log at `0x1800C04F5` (large processing segment `0x1800BF8C7..0x1800C1302`).
- `FtComputeDescriptors_x_2` time log at `0x1800C11D1`.
- Mode 5 references `FtGetMfsFeatures_v2` and `FtComputeDescriptors` in the `0x1800F27D0` family.

The MFS routine names and `sigma/intervals/contrast/curvature` parameters closely resemble **SIFT-style scale-space local feature extraction**; the exact mathematics and thresholds could still be modified.

### Geometry should not yet be assumed

The DLL's initial global data contains `0x180225C40 = 96` and `0x180225C44 = 96` as 32-bit integers, whereas `0x180225C78` begins with the 16-bit pair `64,80`. They may be separate default working/crop/template dimensions; **their individual meanings have not been established**, and they may be changed in initialization. The sensor transport's previously confirmed 64×80 raw samples do **not** by themselves prove that every internal feature extractor consumes a 64×80 buffer directly. Resolving any reshaping/cropping/padding before feature extraction is a priority.

## What this means for our Linux implementation

This substantially refines the earlier model: before creating a SIFT-only prototype, **establish which algorithm mode Windows initializes for this 5955**. If it remains at the DLL's compiled default 1, reproducing MFB/BRISK-named keypoints and descriptors is higher priority than reproducing MFS/SIFT. If mode is changed to 2/3/4, MFS becomes relevant. Mode 5 is its own pathway.

The synthetic-tested reconstructed grayscale converter remains separate and is not yet verified against actual Windows output. Likewise, the presence of MFB/BRISK or MFS/SIFT function names does **not** mean a stock third-party implementation is compatible with FocalTech's template format or scoring.

**Recommended next read-only reverse-engineering actions:**
1. Trace the `focal_SetAlgoMode` setters and startup calls in the DLL to determine whether `0x180225C51` is overridden for this USB model.
2. Trace the MFB detector's `0x1800C41B0`/`0x1800C4610` sequence and MFB descriptor subroutine around `0x1800C8990` to recover coordinate handling, orientation bins, feature length, pair comparisons and mask handling.
3. Trace the `FtGetTemplate` caller's input image buffer through any geometry transformations to resolve why 96×96 and 64×80 constants coexist.
4. Validate on synthetic arrays before private, local-only genuine captures. Do not modify login, Windows Hello, fprintd or the existing USB bridge.

### Reproduce the key disassembly privately (on Nobara)

```bash
DLL=/path/to/private/ftWbioEngineAdapter.dll
sha256sum "$DLL"
llvm-objdump -d --x86-asm-syntax=intel \
  --start-address=0x180036490 --stop-address=0x180036675 "$DLL"
llvm-objdump -d --x86-asm-syntax=intel \
  --start-address=0x1800C14F0 --stop-address=0x1800C15E5 "$DLL"
llvm-objdump -d --x86-asm-syntax=intel \
  --start-address=0x1800C2CC0 --stop-address=0x1800C2D30 "$DLL"
```

These commands disassemble the locally held DLL without executing Windows code or reading biometric data.


## Recovered MFB 256-bit comparison descriptor

A deeper disassembly of `0x1800C8990`, which is **directly called twice** by the MFB descriptor stage (`0x1800C32F5` and `0x1800C3322`), reveals the actual descriptor encoding, not merely suggestive BRISK function names:

1. **45 radial sampling positions.** A 45-entry read-only array beginning at `0x1801EAE20` consists of 2D `float32` points on three circles: **10 points at radius 4, 15 at radius 8, and 20 at radius 13**. `0x1800C8B46` sets the `0x2D` (=45) sample loop count; `0x1800C8B50..C8C06` rotates/translates each sampling position and reads an image float. The coordinate transform includes cosine/sine-like factors read from the feature and ±0.5 adjustment before float-to-int truncation, then bounds checks against image width/height (`0x1800C8BC0..C8BED`). An invalid point is represented by `-1.0f` (`0x1801FC980`). The precise orientation angle convention and scale normalisation are not yet fully characterized.
2. **256 selected comparisons.** A 512-byte table beginning at `0x1801EAC20`, immediately **before** the radial points, contains **256 distinct-index pairs**. Each of its 512 unsigned-byte indices is in `0..44`, covering all 45 positions, and no pair compares an index with itself. The table's proprietary contents are **not copied into Git**.
3. **Bit generation.** At `0x1800C8C18`, the code sets `r9d = 0x40` (64 groups). Every iteration processes four 2-index comparisons (`0x1800C8C35..C8D43`). It loads two valid sampled intensities, skips the comparison if either is negative, and executes `bts` to set its output bit when the second intensity is less than the first (e.g. `comiss` at `0x1800C8C52`, `bts` at `0x1800C8C5B`). That is **64 × 4 = 256 binary decisions**.
4. **Exact per-feature record size.** The MFB stage allocates `0x2C` (=44) bytes per feature at `0x1800C32C9`, confirmed again by the output-record stride at `0x1800C8D87`. The descriptor lives at offsets `+0x0C..+0x2B`, i.e. **32 bytes / 256 bits**. The first 12 bytes are three copied 32-bit fields from the detected feature object (`0x1800C8D49..C8D59`); those fields' exact semantic labels remain unresolved.

**This is the first byte-/instruction-level recovery of the mode-1 FocalTech descriptor.** It is strongly consistent with a custom BRISK-style binary local descriptor, but **not** evidence that ordinary OpenCV BRISK produces the same 256 bits. Feature **detection**, orientation, scale, thresholds, template serialization and final score remain unverified.

### Reproducible private-binary audit

A dependency-free, read-only audit script is available at [`tools/audit_moh_engine_features.py`](../tools/audit_moh_engine_features.py). It checks the exact researched DLL SHA256 and PE layout, validates the initial algorithm parameters, 45 concentric sample points, 256 indexed intensity pairs, and selected instruction signatures for the loop/bit/record stride. It prints **only aggregate configuration and structural counts**, not proprietary lookup bytes, and never opens biometric captures. It has been executed successfully against the private matching engine DLL in an isolated local analysis environment.

```bash
python3 tools/audit_moh_engine_features.py /path/to/private/ftWbioEngineAdapter.dll
```

This is not a feature-extraction implementation, and it is not connected to Windows Hello, libfprint or USB acquisition. Full feature-extractor equivalence will require reconstructing the interest-point detector and scale/orientation transform before any real-sample matching claims are possible.


## Image-pyramid and keypoint-detection sequence

Additional **direct cross-references and log strings** in the matching engine resolve much more of the first half of the **mode-1 MFB pipeline**:

| Step | Code evidence in MFB extractor `0x1800C14F0` | Cross-check against alternate MFS extractor |
| --- | --- | --- |
| Initial image setup | `FtCreateInitImg` call at `0x1800C18EC` → helper `0x1800C36C0` | MFS calls the same helper at `0x1800BEFCD` |
| Gaussian scale-space pyramid | `FtBuildGaussPyr cost` log referenced at `0x1800C1A9E` | MFS log at `0x1800BF165` |
| Difference-of-Gaussian pyramid | `FtBuildDogPyr` helper `0x1800C41B0` called from `0x1800C1C01`, with elapsed-time log at `0x1800C1C57` | MFS calls same helper at `0x1800BF2D6`, log at `0x1800BF32C` |
| Scale-space keypoint extrema | `FtScaleSpaceExtrema` elapsed-time log referenced at `0x1800C1E7A`; near call `0x1800C1E21` → `0x1800C4610` | MFS corresponding log at `0x1800BF63B` |
| Orientation of MFB features | `FtCalcBriskFeatureOris cost time` log referenced at `0x1800C2CE4` | MFS uses distinct `FtCalcMfsFeatureOris` |
| MFB feature description | `FtMfbDescriptors_x_2` log at `0x1800C3376`; directly calls `0x1800C8990` at `0x1800C32F5` and `0x1800C3322` | MFS uses `FtComputeDescriptors_x_2` |

**Working architectural sketch, with stages anchored to observed calls/logs:**

```text
FocalTech driver 8-bit image
    → FtCreateInitImg
    → Gaussian scale-space pyramid
    → Difference-of-Gaussian pyramid
    → scale-space extrema / keypoint candidates
    → MFB orientation (BRISK-named)
    → per-keypoint 45 rotated sample positions
    → 256 ordered intensity comparisons
    → 256-bit binary descriptor in a 44-byte feature record
    → vendor template construction
    → downstream geometric matching / RANSAC / match scores
```

The **shared Gaussian/DoG/scale-space detector** is a notable finding: BRISK-named MFB orientation/description does *not* prove the keypoint detector is standard BRISK. This DLL apparently combines a Gaussian/DoG-style keypoint pipeline with a **custom 256-bit BRISK-like descriptor**. We have **not** established byte-for-byte conformity with SIFT, BRISK, OpenCV, or the exact detector octave/threshold/refinement rules, nor the real runtime algorithm-mode value.

**Next missing instruction-level information:** inspect `0x1800C4610` (extrema selection, refinement and acceptance thresholds), the keypoint-orientation path around `0x1800C20EB..0x1800C34D0`, and the three 32-bit metadata fields preceding each descriptor. Validate these using synthetic images independently from Windows Hello.
