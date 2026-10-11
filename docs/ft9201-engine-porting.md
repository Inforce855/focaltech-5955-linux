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

The 64-row-wrap hypothesis is consistently distinguished by unusually large boundary jumps in all four captures and much smaller adjacent-row differences. Combined with the Windows stride and visual evidence, **64 x 80 should be the primary *working assumption* for sensor memory geometry**. This is not a formal guarantee: line-specific sensor bias, blank edges, fixed patterns or firmware row remapping could influence the seam measurement. Do not conflate '64x80' with 'rotating a finished 80x64 image': the raw sample arrays are *re-wrapped*, not rotated.

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

**Never send FT9201 firmware, register writes, power/reset commands or control transfers to our `5955`**. No changes to Nobara USB services, system libraries or authentication components. The transport should be built on our **already validated `5955` USB protocol**, with bounded reads and device validation.

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

## MOH 5955 Windows engine-adapter export check — 11 October 2026

The owner located a `ftWbioEngineAdapter.dll` in their existing **MOH** FocalTechFPSSOdriver25H2x64V5.10.66.6611_WHQL package alongside the matching `FtWbioDriverUmdfV3` driver. The separate **MOC** FT9365 v3.95.6501.6448 package also contains a similarly named DLL **plus** `ftSecureEngineAdapter.dll`, but must not be treated as the same device implementation.

The owner ran `file` and `objdump -p` locally on the **MOH** DLL, reporting:

- PE32+ Windows DLL, **x86-64**, seven sections.
- Exported function: **`WbioQueryEngineInterface`**.
- Imported modules: **`KERNEL32.dll`, `ADVAPI32.dll`, `SETUPAPI.dll`**.
- No `CreateEnclave` / `CallEnclave` names shown by the targeted export/import grep. This is **not** proof no enclave, dynamic security dependency or loader complication exists.

**Significance:** This confirms a plausible native WinBio engine integration approach for the correct transport-family package, and narrows the first task to compatibility analysis of the DLL ABI, imports and engine-specific image format. OMGrant's FT9201 PE loader registers mainly `kernel32` shims, and resolves *function symbols by name* (its import loop does not even select dispatch by imported module name). Therefore the extra DLL names **alone** do not prove it will fail; the **specific imported functions** matter. Any unimplemented import is written as a null IAT entry and calling it can crash: do not execute or install the DLL with an unmodified loader.

### Next read-only action

List the specific imported functions in `ADVAPI32.dll` and `SETUPAPI.dll`, and verify the MOH INF's engine registration and exact hardware IDs. Use only shell read-only tools, no DLL execution, firmware uploads, USB messages, enrollment or biometrics.

Example local import inspection (MOH shell variable points to the owner-provided package directory):

```bash
objdump -p "$MOH/ftWbioEngineAdapter.dll" | awk '
  /DLL Name:/ { dll=$3; next }
  (dll == "ADVAPI32.dll" || dll == "SETUPAPI.dll") &&
  /^[[:space:]]*[0-9a-fA-F]+[[:space:]]+[0-9a-fA-F]+[[:space:]]/ { print dll, $3 }
'
```

Do not upload proprietary DLL/INF, biometric captures or reconstructed templates to the public repository. Record only general technical metadata.


## MOH engine static imports: ADVAPI32 and SETUPAPI (11 October 2026)

The device owner used read-only `objdump -p` on the locally held **MOH** `ftWbioEngineAdapter.dll` matching the FocalTechFPSSOdriver25H2x64V5.10.66.6611 Windows package. This is static import metadata only: no proprietary binary or actual biometric data is committed.

**ADVAPI32.dll — seven imports:**

- `RegQueryValueExA`
- `RegOpenKeyExA`
- `RegCloseKey`
- `ReportEventA`
- `RegisterEventSourceA`
- `DeregisterEventSource`
- `RegSetKeyValueA`

**SETUPAPI.dll — five imports:**

- `SetupDiDestroyDeviceInfoList`
- `SetupDiEnumDeviceInfo`
- `SetupDiGetDeviceInstanceIdA`
- `SetupDiGetClassDevsA`
- `SetupDiClassGuidsFromNameExA`

This totals **12 non-KERNEL32 imports**. Functions support Registry configuration, Windows event logging and device enumeration. They do not prove that cryptography or enclaves are absent: dynamic DLL loading and other dependencies remain possible.

Comparison with [OMGrant's `src/ft_engine.c`](https://github.com/OMGrant/ft9201-libfprint/blob/master/src/ft_engine.c): **none of these twelve names is registered in its existing shim inventory**. Its current PE import resolver looks symbols up by name and writes null entries when missing; merely executing our MOH engine in that unmodified loader may crash. KERNEL32 imports also need a complete differential audit, not just this initial list.

**Implementation constraints:** do not add blanket always-success shims or fake registry/device IDs. Check the MOH INF for the engine adapter registration and device IDs, and trace which registry keys or SetupAPI enumeration the DLL requires; provide bounded, accurate compatibility behavior only where needed. No DLL execution, kernel changes, USB writes, biometric enrollment, template publication, system-libfprint replacement or PAM integration until vetted. A proprietary engine should ultimately be loaded only in a suitably isolated, controlled development harness with trusted provenance.

Immediate read-only local command to inspect the MOH INF (not the MOC/FT9365 package):

```bash
grep -nEi 'VID_2808|PID_5955|EngineAdapter|SensorAdapter|Wbio' \
  "$MOH"/*.inf
```

Do not share or publish the proprietary `.dll` or full driver package; harmless INF matching lines or ordinary import names are adequate for technical evaluation.


## Direct analysis of owner-provided 7_Fingerprint-module.zip (11 October 2026)

The original **4,271,168-byte** `7_Fingerprint-module.zip` had previously been uploaded by the owner and was available directly in the working container. This analysis inspected it in-place, **rather than asking for any further transfers or terminal commands**. All extracted DLLs and INF files remained private in the analysis environment; **no proprietary binaries or biometric data are committed to GitHub**.

### INF identifies our exact 2808:5955 reader

The UTF-16 MOH `FtWbioDriverUmdfV3.inf` (21 November 2025; `DriverVer 5.10.66.6611`) explicitly lists hardware IDs `USB\VID_2808&PID_C6D5`, `USB\VID_2808&PID_65D5`, and **`USB\VID_2808&PID_5955`** at lines 21–23, repeated in the additional installation section at lines 28–30. Its `WinBio\Configurations\0` registers:

- `EngineAdapterBinary = ftWbioEngineAdapter.DLL`
- `SensorAdapterBinary = ftWbioSensorAdapter.DLL`
- `StorageAdapterBinary = ftWbioStorageAdapter.DLL`

This **directly links the uploaded MOH engine to a vendor-provided Windows driver package supporting PID 5955**; stronger than filename matching. It does not independently prove which internal matching mode or geometry is selected for each supported hardware revision.

The *separate* MOC `FtWbioDriverUmdf.inf` includes IDs `0579`, `1579`, `0599`, `059C`, and `1599`; **not PID 5955**. Its separate `ftSecureEngineAdapter.dll` contains bcrypt imports; do not confuse the MOC secure engine with our MOH engine.

### Read-only PE inspection of the matching MOH DLL

- `MOH/ftWbioEngineAdapter.dll`: 2,847,280-byte 64-bit PE DLL, exports `WbioQueryEngineInterface`.
- Its PE import table names **98 functions in KERNEL32**, **7 in ADVAPI32** (`RegQueryValueExA`, `RegOpenKeyExA`, `RegCloseKey`, `ReportEventA`, `RegisterEventSourceA`, `DeregisterEventSource`, `RegSetKeyValueA`), **5 in SETUPAPI** (`SetupDiDestroyDeviceInfoList`, `SetupDiEnumDeviceInfo`, `SetupDiGetDeviceInstanceIdA`, `SetupDiGetClassDevsA`, `SetupDiClassGuidsFromNameExA`).
- KERNEL32 imports also include `FlsAlloc`, `FlsGetValue`, `FlsSetValue`, `FlsFree`, `ReadFile`, `SetEndOfFile`, `ReadConsoleW`, `GetFileSizeEx`, `GetTempPathW`, `Sleep`, `QueryPerformanceFrequency`, `GetLocalTime`, `GetDateFormatW`, `GetTimeFormatW`, `CompareStringW`, `GetLocaleInfoW`, `GetFileAttributesExW`, `InterlockedPushEntrySList`, among others. **Some are not registered by the FT9201 loader**. The earlier belief that 'only 12 extra functions are needed' was **incorrect**; full import coverage and actual call semantics must be audited.
- The MOH sensor adapter exports `WbioQuerySensorInterface`; the MOH storage adapter exports `WbioQueryStorageInterface`, but these are more complex Windows components and are not required for the first standalone matcher ABI study. The storage DLL imports `bcrypt.dll` and `CRYPT32.dll`, even though the **engine DLL itself** does not statically import those libraries.
- Neither an external DLL nor vendor engine code was executed, and no USB messages or biometric operations were performed.

### Implications for porting

Start from the MOH engine's actual imports/exports and original WinBio INF settings. Build an **isolated static compatibility inventory** before running the PE loader. Ensure unsupported shims fail *closed* rather than silently writing NULL into the import address table (the FT9201 loader currently logs missing shim names and fills the IAT with NULL). Avoid fprintd/PAM or native authenticator integration until a properly sandboxed synthetic-image engine smoke test succeeds. Our independently validated 64 x 80 sensor memory layout is highly plausible but still requires testing against the vendor engine's accepted image format.
