# FT9201 WinBio engine research and possible native 2808:5955 port

Date: 11 October 2026. Independent reference: https://github.com/OMGrant/ft9201-libfprint (branch master).

**No real fingerprint images, raw samples, descriptors or templates are included here.** All measurements below are aggregate numerical diagnostics supplied by the device owner.

## Stronger evidence for 64 columns by 80 rows

The physical `2808:5955` reader supplies 5,120 samples in a validated 10,246-byte USB frame. Earlier metadata was called 80 x 64, but the Windows UMDf correction code uses a **128-byte stride (64 two-byte samples)**. The owner independently reported that the 64 x 80 rendering shows more coherent grey fingerprint-shaped contours. The separate `2808:c652` code also uses 64 x 80.

From a **second independently captured A1/A2/B1/B2 set**, the offline little-endian row-boundary probe found:

| Capture | 64-sample median seam jump / within-row jump | 80-sample seam jump / within-row jump | Vertical-neighbour median difference (64 / 80) |
| --- | ---: | ---: | --- |
| A1 | 9.96x | 1.32x | 64 / 180 |
| A2 | 5.48x | 1.37x | 88 / 188 |
| B1 | 6.39x | 1.09x | 52 / 204 |
| B2 | 8.27x | 0.90x | 68 / 260 |

The 64-row-wrap hypothesis is consistently distinguished by unusually large boundary jumps in all four captures and much smaller adjacent-row differences. Combined with the Windows stride and visual evidence, **64 x 80 should be the primary *working assumption* for sensor memory geometry**. This is not a formal guarantee: line-specific sensor bias, blank edges, fixed patterns or firmware row remapping could influence the seam measurement. Do not conflate '60x80' with 'rotating a finished 80x64 image': the raw sample arrays are *re-wrapped*, not rotated.

## OMGrant/ft9201-libfprint: architectural relevance

Reference URLs:

- https://github.com/OMGrant/ft9201-libfprint/blob/master/README.md
- https://github.com/OMGrant/ft9201-libfprint/blob/master/PORTING.md
- https://github.com/OMGrant/ft9201-libfprint/blob/master/docs/how-it-works.md
- https://github.com/OMGrant/ft9201-libfprint/blob/master/src/ft_engine.c
- https://github.com/OMGrant/ft9201-libfprint/blob/master/src/ft_engine.h
- https://github.com/OMGrant/ft9201-libfprint/blob/master/src/ft9201.c

The author reports working Linux enrollment and verification through a patched **native `libfprint` driver** for **Focal-systems `2808:93a9` / FT9348W**, a **96 x 96** standalone optical reader. The device supplies raw frames to a **proprietary Windows FocalTech engine DLL** (`ftWbioEngineAdapter.dll`). A small C PE loader (`src/ft_engine.c`) runs the vendor matcher inside Linux without Wine by providing enough `kernel32` imports, a fake x64 Windows TEB, the WinBio engine interface and a storage adapter. Their PE image is mapped without simultaneously writable and executable pages (intended to preserve fprintd hardening). No vendor engine binaries are committed in that repo.

The **matcher** expects an **8-bit 64 x 80 WinBio BIR**. On the FT9201 only, the driver converts the native **96 x 96 image into a 64 x 80 centre crop**, preserving ridge spacing. The README reports successful enroll/verify when using this engine-specific size, and failed genuine matches using 96 x 96 directly. That strongly supports investigating a 64 x 80 *image/engine interface*, but does **not** prove the exact `2808:5955` Windows engine will accept the FT9348W format or be interchangeable with the DLL from the FT9201 package.

### Device-specific USB differences: do not reuse FT9201 transport

| Aspect | FT9201 `2808:93a9` | Our `2808:5955` |
| --- | --- | --- |
| USB OUT / IN | 0x02 / 0x83 | 0x01 / 0x82 |
| Native image | 96 x 96 optical, cropped for matcher | 5,120 16-bit samples; 64 x 80 emerging |
| Bring-up | FT9348W MCU firmware upload and register-config sequence | Existing FT936x firmware already responds to validated image/handshake commands |
| Capture protocol | Different control/firmware state machine | Known 0x81 reads and verified status semantics |

**Never send FT9201 firmware, register writes, power/reset commands or control transfers to our `5955`**. No modifications to existing CFS or OS components. The transport should be built on our **already validated `5955` USB protocol**, with bounded reads and device validation.

## Enrolment: repeated, repositioned impressions are required

Our previous A1/A2/B1/B2 tests are *single-image diagnostic pairs*, NOT a multi-stage enrolled template. Users deliberately lift and reposition a finger between stages to supply partially overlapping contact regions with different placement and rotation.

The FT9201 libfprint driver sets `nr_enroll_stages = 8`. In its implementation:

1. Start an enrolment with `ft_engine_enroll_begin()`;
2. Capture a new impression after the user places and lifts the finger;
3. Pass the correctly formatted frame using `ft_engine_accept(..., purpose=4)`;
4. Call `ft_engine_enroll_update()`: 0=complete, 1=more images required, 2=frame rejected (e.g. duplicate region/low quality);
5. On sufficiently varied coverage, `ft_engine_enroll_commit()` produces an **opaque matcher template** kept private within an `FpPrint`;
6. Verification feeds a new impression with purpose=1 and compares to that **enrolled** template, not just the previous capture.

Stage count is a driver setting and may differ for our chip and DLL. Failed/duplicate captures must not be counted as completed stages. **Do not automatically average or stitch unaligned captures**; rely on a validated template engine or robust quality and overlap checks.

## Suggested staged port (no system installation now)

**Stage A: static vetting** — determine whether the *matching Windows package for `2808:5955`* includes `ftWbioEngineAdapter.dll` or another DLL exporting `WbioQueryEngineInterface`. Inspect only local binary metadata (DLL names, imports, exports) and the package INF adapter registration; avoid uploading proprietary files. Determine supported chip/geometry. The FT9201 DLL is a separate vendor binary and cannot be assumed compatible.

**Stage B: isolated engine harness** — if there is a compatible WinBio engine, adapt the **LGPL-2.1-or-later** PE loader and bridge behind a *separate offline experiment* with synthetic 64 x 80 test images. No biometric database, fprintd/PAM changes or PC login integration. Check basic engine initialization and BIR format before consuming private samples. The vendor DLL is proprietary and must stay local. Review security implications of running a foreign binary in-process.

**Stage C: private offline multi-scan validation** — with the owner's explicit approval, use a staged sequence of multiple repositioned impressions (e.g. 8 per enrolled finger) on 5955. Quality-gate captures, track acceptance/retry, enroll, then verify on *new* captures of genuine and unrelated fingers. Avoid hardcoded security thresholds inferred from a single test. Preserve samples/templates exclusively in a private, access-controlled local store; do not print biometric content.

**Stage D: native Linux `FpDevice`** — implement verified USB capture and finger-present/off controls with cancellation/timeouts, enrol/verify callbacks, status reporting, and private opaque-template management. Integrate into a pinned out-of-tree libfprint test build without replacing Nobara system components; evaluate errors and security before any `fprintd`/PAM adoption.

**Compatibility and redistribution:** the FT9201 source is LGPL-2.1-or-later; respect its source-license terms if adapting. Its separately downloaded proprietary Windows DLL is not open source. A solution based on that vendor matcher is native Linux *integration* but not a completely open-source matching stack. Run the DLL only with trusted provenance; do not weaken OS hardening or bypass transport security.

## Immediate next action

Identify the `2808:5955` Windows driver package's registered engine adapter and its exports **before** adapting code. If that DLL is absent, the FT9201 adapter may still provide architecture insight, but cannot be presumed to work with our scanner. This is more important than another correlation/SIFT tuning pass.
