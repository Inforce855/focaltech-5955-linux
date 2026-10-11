# Reverse-engineering the MOH WinBio engine for a fully native Linux matcher

Research date: 11 October 2026. This is an interoperability research plan, **not a working authenticator**.

## Scope and exact reference

The relevant proprietary file is **MOH** `ftWbioEngineAdapter.dll` from the user's original `7_Fingerprint-module.zip`, in `FocalTechFPSSOdriver25H2x64V5.10.66.6611_WHQL`. Its companion MOH INF explicitly includes `USB\VID_2808&PID_5955` and identifies the WinBio engine/sensor/storage adapter DLLs. This is **not** the FT9365 MOC package. Static binary inspection used `strings` / PE metadata only, without executing the DLL, accessing USB or using actual fingerprint samples.

The objective is to explore a **fully native, independently implemented Linux matcher with no Windows DLL required at runtime**. This is a larger goal than OMGrant's native libfprint transport + **Windows matching DLL** compatibility bridge. OMGrant's architecture is still potentially useful as a controlled reference engine, not our only route.

## Concrete, static evidence inside this actual DLL

The binary contains vendor development path `D:\work\Sensor\FT9366\newarch\commit\MOH_engineAdapter\algo\src\algo_focal.cpp` and related engine adapter source path strings. These paths do **not** contain original C++ source: they are debugging text embedded in compiled native code.

| Suspected stage | Recoverable internal names and logging tokens | Interpretation limits |
| --- | --- | --- |
| Sensor layout and image mode | `focal_SetFpSensorColsRows`, `focal_SetImageBit`, `focal_SetImageNoiseFilter` | Need trace image byte-order, bit-depth and actual transforms in UMDF + WinBio code |
| Quality and contact coverage | `focal_GetImageQuality`, `coverage`, `quality`, `humdity`, `over_exposure_coverage`, `enroll_minArea_threshold`, `enroll_score_threshold` | Scores/thresholds not yet recovered and must not be invented |
| Scale-space features | `FtGetMfsFeatures`, `FtGetMfsFeatures_v2`, `FtGetMfbFeatures`; logging parameters `sigma`, `intvls`, `contrThr`, `curvThr` | Strongly suggests a DoG/SIFT-like detector, not proof of standard SIFT compatibility |
| Feature orientation/descriptors | `FtCalcMfsFeatureOris`, `FtMfsOriHist`, `FtComputeDescriptors`, `FtMfbDescriptors_x_2`; `gauss_pyr`, `dogPyr` | Actual descriptor layout, sizes and normalization remain unknown |
| Geometric alignment/matching | `FtRansacNew`, `FtRansacAngle_32f`, `FtVerifyTwoTemplate`, `H_matrix`; log fields `ransacScore`, `binScore`, `recallScore`, `matchScoreThr`, `overlapArea` | Indicates RANSAC-like point alignment with extra binary/recall scoring, not a single stock OpenCV matcher |
| Enrolment and storage | `FtEnrollByTemplate`, `focal_EnrollByImage`, `focal_IdentifyByImage`, `FtSubTemplateCopy`, `template_import`, `template_export`; template logging `nFeatureNum`, `featBufSize`, `binBufSize`, `maskBufSize` | Multiple subtemplates and distinct feature, binary discriminator and mask fields are indicated; blob format not recovered |
| Repeat/impression coverage | `focal_EnrollmentDuplicateCheckEn`, `focal_SetEnrollMaxTpl`, `enroll_angle_threshold`, `focal_SetRescanOverlapAreaThreshold` | Consistent with multi-stage enrolment but not a verified algorithm description |

Important subtlety: these are **text/log references found within proprietary binary machine code**, not exported function entry points or an automatically recoverable C++ API. The DLL has about 1.76 MB of `.text` machine code, including library/runtime code. Recovering exact algorithms, constants, internal data structures, and matching quality is substantial reverse-engineering effort.

## What our OpenCV SIFT test did and did not prove

The earlier `tools/sift_compare.py` performed a generic bicubic/CLAHE preprocessing + OpenCV SIFT keypoint and RANSAC comparison. 64 × 80 yielded many more keypoints than 80 × 64 but only 5–6 RANSAC inliers in both genuine and impostor comparisons. This **does not** disprove FocalTech's custom algorithm: we have not reconstructed its image calibration, detector, descriptor, geometric thresholds, extra `binScore`/`recallScore` evidence or multi-template enrolment. This experiment merely shows generic SIFT is inadequate as currently configured.

## A realistic, low-risk reverse-engineering sequence

1. **Establish image ingress**: trace `EngineAdapterAcceptSampleData` / `WINBIO_BIR` and the companion `FtWbioDriverUmdfV3.dll` correction path; confirm exactly how a 64 × 80 grid of 16-bit USB readings becomes the algorithm's input (bit depth, polarity, calibration, background, whether 8-bit BIR). No USB tests or firmware changes.
2. **Map function boundaries and call relationships** in the static PE using Ghidra or equivalent, starting at WinBio exports/interface vtable, source-file log strings, `algo_init`, `focal_GetImageQuality`, feature extraction, and template comparison. This is a detailed control/data-flow mapping task, not just symbol listing.
3. **Reconstruct structures and calculations**: feature detector pyramid and thresholds, orientation, descriptor storage, RANSAC geometry, binary/mask/recall scoring, and serialization of partial templates. Keep evidence/proposed pseudocode separate from a new independently authored implementation.
4. **Native, offline prototypes**: first input image correction and quality gating, then feature extraction, then geometrical scoring, then non-biometric synthetic multi-impression template testing. Keep all real biometric samples private and never store or publish fingerprint media, descriptors or actual templates.
5. **Validate with genuine and impostor fingers on this exact reader**, using re-positioned multistage enrolment and captures withheld from enrolment. Establish repeatability, false accepts, false rejects and quality-based retries before evaluating fprintd/PAM authentication.

Optional short-cut: OMGrant's LGPL WinBio PE loader could serve as an **isolated local-only reference** to query the vendor engine with synthetic input, helping confirm ABI or numerical behavior. It still executes closed-source Windows code, needs more than the FT9201's KERNEL32 shims for our MOH engine, and must not be used in login paths or attached to USB during early tests. The *end goal* can remain a matcher implemented entirely for Linux with no vendor DLL dependency.

## Hardware and legal constraints

- Reader `2808:5955` recovery under Linux is not guaranteed; user will **not run Windows on bare metal**. No unknown hardware reset, firmware flashing, guessed USB commands or kernel drivers.
- Static analysis and offline synthetic tests do not interact with the sensor.
- Proprietary binary contents and biometric samples are not committed. Preserve attributable source references. For an eventual redistributed native implementation, consider applicable interoperability/reverse-engineering laws and clean-room implementation practices.
- Do not confuse *a native Linux libfprint driver that calls a vendor DLL* with a *fully native open-source fingerprint matcher*; these are two different engineering goals.


## Discovery: existing native Linux FocalTech matcher binaries and related open research (11 October 2026)

The hypothesis that FocalTech reuses algorithm components across its sensor variants now has several concrete leads. This does **not** establish compatible USB commands, calibration tables or bit order between models. Keep our 5955 hardware offline during reference-library analysis.

1. [leopalladium/focaltech-ft9366-arch-shim](https://github.com/leopalladium/focaltech-ft9366-arch-shim) hosts a **7,600,216-byte compiled x86-64 Linux `libfprint-2.so.2.0.0`**, repackaged for FT9366 `2808:a658`. This is a **proprietary binary**, *not* algorithm source. It may be useful for read-only ELF symbol/string/disassembly analysis, never drop it into the system or overwrite Nobara's libfprint.
2. [pccr10001/ftfp_proxy](https://github.com/pccr10001/ftfp_proxy), especially [`src/vendor_bridge.c`](https://github.com/pccr10001/ftfp_proxy/blob/main/src/vendor_bridge.c), refers to an **internal, not dynamically exported** native function `ft9362_histNormalize` at *version-specific* `0x4f510`, as a function of signature **`void(int16_t *src, int width, int height, uint8_t *dst)`**. This is a highly relevant static lead for the **16-bit sensor sample → 8-bit normalized image** stage on some FocalTech Linux builds. The offset may be wrong for other builds, and the exact sign, scale, layout and calibration need disassembly confirmation. Never blindly jump to an internal binary offset.
3. [AlecSchneider/onexplayer-superx-ft9366-fingerprint](https://github.com/AlecSchneider/onexplayer-superx-ft9366-fingerprint) reports successful fingerprint enrollment and verification on **`2808:5952`** using a modified FT9366 native binary path. Nearness to our **`2808:5955`** is intriguing, **not evidence of compatibility**, and its binary patch/udev/PAM/installation instructions are prohibited for our hardware-safety-first project.
4. [inevitableDivu/focaltech-2808-6658-driver](https://github.com/inevitableDivu/focaltech-2808-6658-driver) is an experimental open-source **transport** for `2808:6658`, with EP OUT `0x01`, IN `0x82`, 5120 16-bit sensels and a 64×80 display layout in its code. **Its wire protocol is distinct** (register/SRAM ops such as `08 f7`, `04 fb`, `06 f9`; documented big-endian samples) from our validated `02 00 length ... XOR` framed command transport and LITTLE-endian capture. No extrapolation of firmware registers, image commands, resets or byte order to 5955. Its matcher is still experimental.
5. [mrrbrilliant/ft9201-static](https://github.com/mrrbrilliant/ft9201-static) hosts a roughly 5.0 MB older compiled Linux libfprint supporting another FocalTech family. May offer cross-version symbols or firmware architecture insight.

The proprietary library existence is a **breakthrough for static analysis**, not yet a fully native *open-source* matching implementation. We still need to reconstruct algorithmic stages and validate false accepts/false rejects on our device.

### Highest-value next offline task

Perform **ELF static symbol/relocation/string and function-call graph reconnaissance** on the FT9366 native Linux library in an isolated read-only analysis environment. Specifically locate the function containing or corresponding to `ft9362_histNormalize` and any `FtEnrollByTemplate`, `focal_IdentifyByImage`, feature descriptor, quality check or `FtVerifyTwoTemplate` analogues. Cross-reference these with the matching MOH Windows engine adapter, keeping each binary's version documented. Then independently implement the easiest confirmed operation (likely normalization) on synthetic 64 × 80 16-bit inputs before considering matching.

Redistribution caution: FocalTech library is proprietary; keep it out of our public GitHub, respect applicable license and interoperability rules, and write independent Linux code. These libraries are **not** drop-in modules for 5955. No firmware uploads, VID/PID table patches, kernel module installs or PAM modifications.
