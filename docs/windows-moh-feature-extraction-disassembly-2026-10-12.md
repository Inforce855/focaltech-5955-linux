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
