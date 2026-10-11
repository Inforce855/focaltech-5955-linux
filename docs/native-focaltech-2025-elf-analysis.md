# Native FocalTech Linux binaries recovered from 19 February 2025 packages

Analysis date: 11 October 2026. User provided the **Ubuntu `.deb` and Red Hat self-extracting `.install`**, both previously recovered from a web archive. Read-only static inspection only. **Neither binary was installed, linked, dynamically loaded or executed. No hardware accessed, fingerprints read or personal biometric media included.**

## Contents, hashes and executable safety

| Origin | Package / extraction | Native file size | SHA-256 of private extracted ELF |
|---|---|---:|---|
| Ubuntu | `libfprint-2-2_1.94.4+tod1-0ubuntu1~22.04.2_amd64_20250219.deb`, member `usr/lib/x86_64-linux-gnu/libfprint-2.so.2.0.0` | 7,309,376 bytes | `f34e3fac69800700ff9e3a4fa42116073bf98cea7966f7ab56537c82e836d748` |
| Red Hat | `libfprint-2-2_1.94.4+tod1_redhat_all_x64_20250219.install`, embedded tar.gz member `usr/lib64/libfprint-2.so.2.0.0` | 7,253,984 bytes | `5b1508ca3846f50e06044463c7e2c4244330d676752ddf4b0bc28a2c4110495d` |

The `.install` file is **an executable Bash installer plus compressed tar archive**. Its script would invoke `sudo tar ... -C /`. **Never execute it** on the user's Nobara PC. Its contents were inspected as an archive with no installation scripts run. The `.deb` was unpacked to a temporary private analysis directory without executing any dpkg maintainer script. These proprietary binaries **must not be checked into the public repository**.

## Substantial breakthrough: binaries contain ELF .symtab AND DWARF debug info

Both ELF libraries are **not stripped**. Each includes `.symtab`, `.strtab`, `.debug_info`, `.debug_line`, `.debug_str`, and other debugging sections. The Ubuntu library carries **4,189 defined named symbol entries** (including code, data and source-file names); roughly **2,391 local/defined text symbols**. This is vastly more actionable than a Windows PE with only one exported WinBio API entry. DWARF can disclose source-file names and line mappings / declarations but **not the original source code**.

The Ubuntu binary's symbol table directly identifies these *compiled native functions* (ELF relative virtual addresses shown as provenance clues, **NOT stable external APIs**):

| Stage | Static symbol | Ubuntu ELF address | Red Hat ELF address |
|---|---|---:|---:|
| Image normalisation | `ft9362_histNormalize` | `0x4f510` | `0x4c810` |
| Image quality | `focal_GetImageQuality` | `0x7b9d0` | available in symbol table (exact address not audited) |
| Set sensor geometry | `focal_SetFpSensorColsRows` | `0x75fa0` | `0x71ec0` |
| Multi-impression enrolment | `focal_EnrollByImage` | `0x7d550` | available |
| Identification | `focal_IdentifyByImage` | `0x94c70` | available |
| Feature extraction | `FtGetMfsFeatures` | `0xe0450` | available |
| Descriptor calculation | `FtComputeDescriptors` | `0xde190` | available |
| RANSAC matching | `FtRansacNew` | `0xfd1b0` | available |
| Template verification | `FtVerifyTwoTemplate` | `0xcb250` | available |
| Template enrolment | `FtEnrollByTemplate` | `0xd2520` | available |

Available original C source *filenames* in the symbol table include `FtAlg.c`, `FtImgProc.c`, `FtImgEnhance.c`, `FtImgQualityCalc.c`, `FtMatchCheck.c`, `FtTemplateCrossCheck.c`, `FtCore.c`, `FtStretch.c`, `FtSmooth.c`, `FtBadPixRepair.c`, `focaltech.c`, `ft9362_image_processing.c` and `ft9366.c`. Filenames indicate code provenance and give anchors for reverse-engineering; these are not extracted C source files.

### Crucial cross-reference with the third-party FocalTech proxy

[pccr10001/ftfp_proxy](https://github.com/pccr10001/ftfp_proxy/blob/main/src/vendor_bridge.c) hard-codes `FT9362_HIST_NORMALIZE_OFFSET=0x4f510`. **Our recovered Ubuntu ELF contains that exact symbol at exactly `0x4f510`**, independently confirming the third-party reference applies to this Linux binary build. **The Red Hat copy has the same function at `0x4c810`, not `0x4f510`.** Never call a hard-coded offset across different library revisions.

Read-only disassembly shows the Ubuntu normalisation routine negates signed 16-bit input words **in place** and subsequently constructs/smooths an **approximately 256-bin histogram**, before mapping the result. Thus this is more than simply reinterpreting the bytes or a naive percentile stretch. We have **not** reconstructed the complete mathematical transformation, boundary conditions or pixel polarity, and executing this binary against real private prints is not part of this result.

### Compatibility caveat

Both packages embed native Linux fingerprint matcher/processing code; **neither has yet been verified to identify or support USB PID `2808:5955`**. The fact that a developer compiled FT9366/FT9362-related code into these binaries does not prove they would recognise 5955, nor that these images use the same calibration. They are read-only **algorithm references**, not a recommendation to install a replacement libfprint or patch VID/PID.

### Immediate native research steps

1. Trace `ft9362_histNormalize` with its local subcalls and DWARF line data; independently implement a portable, bounded **synthetic-only** 16-bit-to-8-bit transform and regression tests in our own source.
2. Map the larger vendor library's feature extraction (`FtGetMfsFeatures`, `FtComputeDescriptors`), quality (`focal_GetImageQuality`), enrolment and template matching (`FtEnrollByTemplate`, `FtVerifyTwoTemplate`) in parallel with the *correct* 5955 Windows MOH engine.
3. Keep provenance straight across **three different binaries**: Windows MOH 5955, Ubuntu 2025 native Linux, Red Hat 2025 native Linux. Prefer source-independent behaviour over hard-coded offsets.
4. Withhold hardware interactions, external libfprint installation, firmware writes and authentication wiring. Preserve real user fingerprints under gitignored `local-data/` and **never commit personal biometrics, extracted proprietary binaries or templates**.

This discovery establishes **a native FocalTech implementation with plentiful debug metadata exists**, not that a compatible fully open-source biometric matcher is already completed.
