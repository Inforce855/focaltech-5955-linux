# FocalTech 2808:5955: what the Windows matching engine appears to do

**Investigation date:** 12 October 2026. This documents **read-only static inspection** of the matching private Windows MOH `ftWbioEngineAdapter.dll`. No vendor binary, key, enrolled template, real fingerprint pixels, or USB sample is included.

- Private DLL: `MOH/FocalTechFPSSOdriver25H2x64V5.10.66.6611_WHQL/ftWbioEngineAdapter.dll` from the owner's original driver archive.
- SHA256: `a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c`
- PE32+ x86-64; the sole export is `WbioQueryEngineInterface`; imports include `KERNEL32.dll`, `ADVAPI32.dll`, `SETUPAPI.dll`.
- Static embedded source location: `D:\\work\\Sensor\\FT9366\\newarch\\commit\\MOH_engineAdapter\\algo\\src\\algo_focal.cpp`. **This source path is a build artifact, not proof that the USB device is FT9366;** the packaged Windows driver is for the 2808:5955 MOH device we actually tested.

## Strong direct clues in the engine DLL

The following case-sensitive names and diagnostic format strings were observed by scanning the **actual private binary**, rather than assumed from a related FocalTech model:

| Stage | Embedded names / observations | Supportable interpretation |
| --- | --- | --- |
| Fingerprint image quality | `focal_GetImageQuality`; logged `coverage`, `quality`, `humdity`, `over_exposure_coverage`, `acquired_info` | The engine evaluates usable-area / imaging quality independently from recognition |
| Preprocessing | `AutoGaborFilter`, `AutoGaborFilter16`, `focal_SetImageContrastEnhance`, `focal_SetBinImageEnhance`, `focal_SetImageNoiseFilter` | Ridge-oriented filtering, contrast and image enhancement methods are present (whether each is enabled depends on configuration) |
| Multiscale feature detection | `FtGetMfsFeatures`, `FtGetMfsFeatures_v2`, `FtScaleSpaceExtrema`; log includes `sigma`, `intvls`, `contrThr`, `curvThr` | A scale-space interest-point detector similar in structure to SIFT is implemented |
| Orientation/descriptor | `FtCalcMfsFeatureOris`, `FtComputeDescriptors`, `FtComputeDescriptors_x_2`, `FtFeatureCmp` | Keypoint orientations and local visual descriptors are calculated and compared |
| Alternative path | `FtGetMfbFeatures`, `FtCalcBriskFeatureOris`, `FtMfbDescriptors_x_2` | A BRISK-named orientation/binary-feature pathway is present; not yet confirmed as active on this 5955 |
| Template building | `FtGetTemplate...FtGetMfsFeatures sucess!`, `FtGetTemplate...FtGetMfsFeatures cost time = %d ms`, `FtGetTemplate...gEnrolledTemplate[%d]->subtemplates[%d].nFeatureNum[0] = %d`, `nFeatureNum[1]` | Strong evidence the **template-building flow uses MFS local features**, and supports multiple subtemplates/features |
| Template representation | `ST_Feature`, `pTemplateFeature`, `templateBinDiscr`, `templatePixValid`, `featBufSize`, `binBufSize`, `maskBufSize` | Templates contain feature data, a binary-discriminator block and a valid-pixel mask; precise record layout remains unverified |
| Matching/alignment | `FtRansacNew`, `FtRansacAngle_32f`, `FtVerifyTwoTemplate_v2`; diagnostic `before ransac....pointNum = %d`, `after ransac, m = %d` | Robust geometric correspondence/alignment is used in at least one matching path |
| Scoring | `ransacScore = %d, binScore = %d, recallScore = %d, recallEn = %d, matchScoreThr = %d`, `matchScore`, `overlapArea` | Match decisions consider geometric-fit score, a binary score, optional recall score and overlapping image area. Exact scoring and thresholds require disassembly or isolated validation |
| Recognition | `focal_EnrollByImage`, `focal_IdentifyByImage`, `focal_GetImageTemplate`, `focal_VerifyTwoTemplate` | Separate image-to-template enrollment and template comparison APIs exist in the compiled engine |
| Robustness/configuration | `focal_SetMultiAreaMatchEn`, `focal_SetAdjustMatchEn`, `focal_SetImproveFeatureEn`, `focal_SetAlgFarLevel`, `focal_SetTemplateBuffEn` | Configurable multiple-area comparison, feature improvement, acceptance thresholds and template buffering are present |

**Significant evidence:** The `FtGetTemplate` log explicitly says it invokes `FtGetMfsFeatures`, while `FtRansacNew` and the `ransacScore/binScore/recallScore` format string occur in the same engine. This is **much stronger** than simply assuming SIFT because the sensor is small.

## Best current understanding (working hypothesis)

```text
10,240-byte, 64x80 native 16-bit sensor readings
   -> MOH sensor driver's 8-bit spatial/histogram conversion
   -> engine image coverage/quality checks and configurable enhancement
   -> multiscale interest points (MFS) and orientation-aware descriptors
   -> feature-bearing fingerprint subtemplates, valid-pixel mask
   -> candidate feature correspondence + RANSAC geometry/alignment
   -> overlap-aware combined score and acceptance threshold
   -> optionally maintain / update stored templates
```

**Do not confuse direct evidence with a verified control-flow trace.** This flow combines clearly observed function names/log references into a plausible sequence; we have not yet established the 5955's precise runtime `algorithm_mode`, which of MFS/MFB/v2 routines execute, whether BRISK coexists with MFS, actual enhancement settings, binary descriptor layout, score combination, or thresholds. Standard SIFT/BRISK implementations may not exactly match FocalTech's modified `Ft*` variants.

The previously tested generic libfprint NBIS/bozorth3 path returned **zero minutiae** on twenty processed image variants. It is therefore unsurprising that a tuned multiscale local-feature matcher *might* succeed on the same small, partial-print geometry while NBIS does not. **This is a mechanism supported by new static evidence, not yet a demonstrated open-source recreation or cross-sample match.**

## Next safe investigation

1. Continue **offline static tracing** of the matching DLL's `FtGetTemplate` → `FtGetMfsFeatures` and `FtVerifyTwoTemplate` → `FtRansacNew` code paths. Resolve which branch is selected by `algorithm_mode`, feature counts, matching threshold logic, and image dimensions. Keep findings to code structure, public log strings, symbolic offsets and synthetic input tests.
2. Using synthetic images only, validate that an *independent* scale-space keypoint + descriptor + RANSAC prototype is viable at **64x80**. This can establish the mathematics without enrolling anyone's biometrics.
3. Only after isolated validation, consider a private, local-only matcher experiment with the user's own previously captured data and explicit consent. Keep raw files, matching features, BIRs and biometric templates entirely out of Git and chat. Do not alter Windows Hello, PAM, fprintd, or replace the working capture path to conduct research.

## Related public techniques

- [OpenCV SIFT overview](https://docs.opencv.org/5.0/py_tutorials/py_features/py_sift_intro/py_sift_intro.html): explains scale-space extrema, orientation assignment and descriptor matching as a **conceptual comparison**, not proof that FocalTech runs ordinary SIFT.
- [BRISK feature detection/description](https://docs.opencv.org/3.0-alpha/modules/features2d/doc/feature_detection_and_description.html): conceptual comparison for the `FtCalcBriskFeatureOris` string.
- [OMGrant/ft9201-libfprint PORTING.md](https://github.com/OMGrant/ft9201-libfprint/blob/master/PORTING.md): working **different FocalTech reader** (FT9201) leveraging its engine via a Linux PE loader. Not a drop-in solution for 2808:5955.

## Dispatch correction and recovered binary descriptor — 12 October 2026

The original matcher-analysis document identified MFS/SIFT-like and BRISK-named functions by embedded diagnostic strings. A subsequent **direct instruction trace** shows that the compiled **initial algorithm mode is 1**, and `FtGetTemplate` dispatches mode 1 to `FtGetMfbFeatures` (the BRISK-named path), while modes 0/2/3/4 reach MFS and mode 5 reaches MFS v2. Crucially, the MFB descriptor routine has now been recovered at the machine-instruction level: **45 sampling points (radii 4/8/13; 10/15/20 samples), 256 comparisons and a 44-byte record with a 32-byte binary descriptor**. The mode is mutable, so Windows Hello's **actual runtime mode is still unknown**. All evidence, code addresses and caveats: [MOH feature-extraction disassembly](docs/windows-moh-feature-extraction-disassembly-2026-10-12.md).

