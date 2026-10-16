# Archived detailed research roadmap — 11–16 October 2026

> **Historical reference, not current instructions.** Retains the detailed experiments and observations from the older docs/roadmap.md before the 16 October documentation cleanup. Some interim hypotheses and commands are superseded; consult [current project status](../status-2026-10-16.md) and [current roadmap](../roadmap.md).

---

# Development roadmap

## Phase 1 — USB identification (complete)

- [x] Identify USB device ID `2808:5955`.
- [x] Record the interface and bulk endpoints.
- [x] Check installed Nobara `fprintd` / `libfprint` support.
- [x] Identify the matching MOH Windows driver package.

## Phase 2 — Safe diagnostic application (baseline complete)

- [x] Add a descriptor-only diagnostic command.
- [x] Add an explicitly opted-in, timed IN-only listener.
- [x] Run descriptor inspection on the actual Nobara system.
- [x] Test IN-only listening for 15 seconds: **0 non-empty packets**, 11 October 2026.
- [ ] Document non-root device permissions, when needed.

## Phase 3 — Protocol research (in progress)

- [x] Identify an XOR-based `ff_sc_CalcBCC` routine in the matching Windows MOH DLL.
- [x] Locate relevant Windows function-name strings for sensor information and USB communication.
- [x] Compare another FT9366-related project; found major USB interface differences from `2808:5955`.
- [x] Statically reconstruct MOH USB request framing, length and XOR BCC, and basic reply validation (still untested on the hardware).
- [ ] Verify the raw USB bulk pipe and whether a device initialisation sequence precedes the firmware-info command.
- [ ] If needed, capture real Windows USB traffic on user-owned hardware.
- [x] Implement and successfully run a confirmed single-shot firmware-information hardware test (11 October 2026).
- [x] Confirm the firmware-information command works on 2808:5955 and returns ASCII firmware information.
- [x] Correct reply decoding for the verified 50-byte frame followed by one trailing 00 byte.
- [x] Recover the candidate `ff_sc_ReadFingerStatus` request (`02 00 03 82 73 01 f3`) from the Windows MOH DLL.
- [x] Add a one-shot, explicitly confirmed finger-status experiment (not yet run against hardware).
- [x] Verify a real finger-absent reply (`0x06`) and finger-on reply (`0x05`) using the same command.
- [x] Confirm the observed status behaviour on repeated no-finger / finger-present tests and after finger removal (11 October 2026).
- [x] Establish observed basic semantics: `0x05` finger touching, `0x06` finger absent; repeated in separate runs.
- [ ] Implement a rate-limited, interruptible contact monitor if useful (avoid unbounded polling).
- [ ] Determine whether further initialisation is required for event reporting or imaging.

See [protocol research notes](protocol-research.md) and [image acquisition findings](image-acquisition-research.md).

## Phase 4 — Fingerprint functions

- [x] Demonstrate contact and release using repeated one-shot finger-status queries.
- [x] Locate `ff_sc_GetImage`: candidate bulk-image logical request `0x81` (not hardware tested).
- [x] Locate image geometry request path: `0x80` with selectors `03` (height) and `04` (width) (not hardware tested).
- [x] Add a strictly opt-in image-geometry reader; no imaging or raw biometric storage.
- [x] Verify image height via real hardware metadata response: **64 pixels** (`0x40`).
- [x] Verify image width via real hardware metadata response: **80 pixels** (`0x50`); inferred 10,240-byte intermediate raw buffer for 80 × 64.
- [x] Identify a scan-path handshake candidate `0x34` with expected two-byte `0xAA55` marker (DLL analysis only).
- [x] Build an opt-in, one-shot handshake tester (not yet hardware-verified).
- [x] Verify hardware scan handshake `02 00 01 34 35`: correct `55 aa` payload and checksum `f8` (11 October 2026).
- [x] Add a one-shot, explicitly confirmed readiness query (`0x80`, selector `0x01`, two bytes), without scan-mode changes.
- [x] Verify physical readiness response: exact `a5 5a` (`0x5AA5`), valid checksum, with no explicit scan-mode activation.
- [ ] Trace mandatory scan activation, readiness checks and return-to-idle operations before full capture.
- [x] Build and locally test a private offline 16-bit raw-to-PNG converter, with synthetic tests.
- [x] Add a guarded 0x81-only image-read probe that does not modify the separate 0x87 scan mode; bounded private storage; 9 synthetic transfer tests.
- [x] Receive first image-sized transfer on physical sensor: **10,246 USB bytes** on `0x81`, but checksum and pixel content not yet verified; no private capture saved on this attempt.
- [x] Update image transfer parser to allow one unknown trailer byte **only after** a complete 10,245-byte frame passes protocol checksum and length validation.
- [x] Capture and convert physical finger image files under Nobara; owner reported three image files: finger A, finger B, finger A again (11 October 2026). First/third visually similar; second visibly different.
- [x] Observe clearer fingerprint-like detail with **big-endian** raw interpretation; little-endian preview was largely repeated row lines (owner visual inspection; encoding not conclusively proven).
- [x] Add **offline A–B–A image similarity experiment**, with lighting normalisation, ±6 pixel translations, no USB or template storage, and 10 synthetic tests (local tests passed).
- [x] Run A–B–A comparator on real 11 October 2026 data: same finger +0.132; controls +0.078 and +0.130; **+0.003** separation, too weak for authentication.
- [x] Extend the optional offline translation window up to 14px; default remains 6px; do not interpret higher correlations alone as recognition.
- [x] Run the same three private captures with --max-shift 12: A1–A2 unchanged at 0.132; A1–B rose to 0.100, A2–B stayed 0.130; still just +0.003 separation.
- [x] Revisit the matching Windows MOH image converter: its preprocessing at 0x180006184 uses 64-sample/128-byte row strides across 80 rows, suggesting a 64 × 80 intermediate array.
- [x] Add an offline two-layout comparator and an alternative private 64 × 80 PNG rendering option, with synthetic unit tests.
- [ ] Compare private real A–B–A captures in both 80 × 64 and 64 × 80 layouts, and inspect 64 × 80 PNG preview before further algorithm changes.
- [x] Add controlled four-shot **A1, A2, B1, B2** capture mode (`--session --send`), requiring only Enter immediately before each existing `0x81` request; cancelling/failure stops safely.
- [x] Label each real raw capture privately and implement an offline four-capture comparison of two same-finger pairs against all four different-finger combinations.
- [x] Add file-ignore protection for fingerprint-named RAW/PNG files, plus synthetic offline session and comparator selection tests.
- [ ] Test four-capture Enter flow on the actual Nobara PC and review the resulting non-biometric correlation scores.

- [ ] Independently validate pixel interpretation, ridge quality and repeatability with multiple private local comparisons (without sharing biometric data).
- [ ] Validate the image payload and sensor pixel ordering before attempting enrollment.
- [ ] Determine whether the MOH device returns raw images, processed images or proprietary features.
- [ ] Evaluate libfprint image processing/template matching for this device; fall back to a separately vetted matching implementation if necessary.
- [ ] Implement safe enrolment and verification without leaking templates.

## Phase 5 — Linux desktop integration

- [ ] Implement a stable `libfprint` driver or documented alternative.
- [ ] Test through `fprintd` independently of production authentication.
- [x] Confirm experimental native libfprint device enumerates and Claim succeeds through disposable private fprintd/PolicyKit (14 October 2026); **not** an enrolment/verification result.
- [x] Compile v0.9.6 private-fprintd test programmes using `--check` on Nobara (16 October 2026); PASS, no finger scanned.
- [ ] Execute v0.9.6 private `fprintd` enrolment and fresh verification (12 accepted impressions, then separate verification); pending Nobara hardware test.
- [ ] Validate repeated genuine/impostor results and template storage before considering production login.
- [ ] Evaluate reliability, privacy and access controls.
- [ ] Optionally enable KDE / PAM integration once proven safe.

## Explicitly out of scope for the initial release

Firmware flashing, guessed USB command bytes, system fingerprint-library replacement and changing login authentication.

- [x] Run real A1/A2/B1/B2 offline comparison: same-finger +0.089 / +0.081, different-finger maximum +0.118 — no genuine/impostor separation (11 October 2026).
- [x] Identify signed-16-bit input and negative clamp in matching Windows MOH converter (VA 0x180006184); add an offline aggregate-only diagnostic with synthetic tests.
- [x] Run signed-16-bit aggregate diagnostic on four real private captures: little-endian shows 0% signed-negative samples and 99th percentiles 1,616–2,008; swapped big-endian shows 38.9–51.2% negative samples. Strong evidence favours **little-endian** raw words, despite earlier misleading image previews.
- [x] Verify the Windows MOH general converter first clamps signed-negative words and then applies separate sensor-specific correction; negative clamp alone is not sufficient.
- [x] Add private little-endian signed-clamped and optional row-normalised image preview experiments for both 80 × 64 and 64 × 80 layouts, with synthetic tests.
- [ ] Run offline private four-preview experiment on an existing capture, evaluate actual grey sensor patterns separately from any user-added annotations, then revisit matching.

- [x] Capture swapped finger-role A1/A2/B1/B2 session at 14:55 BST: same-pair 80×64 little-endian scores +0.234/+0.197; strongest different-pair +0.201; weak margins +0.032/−0.004.
- [x] Correct premature claim that a higher 80×64 correlation validates row layout: user observes better fingerprint-like *greyscale* structure at 64×80, while quantitative scores change greatly across sessions. Both remain unverified hypotheses.
- [ ] Recompare latest four private captures using little-endian --both-layouts at fixed ±6 px; focus subsequent work on reconstructing the Windows image converter, not threshold tuning.


## Related FocalTech c652 research (11 October 2026)

- [x] Inspect scamiran149/libfprint_focaltechc652 via GitHub: same 0x01/0x82 bulk endpoints, 0x81 image request, 10246-byte image frames and little-endian 16-bit samples.
- [x] Document their explicit 64 x 80 layout, which agrees with the user's visual impression and the MOH 64-sample intermediate row-stride clue.
- [x] Confirm a key protocol incompatibility: c652 treats 82 73 01 as a capture trigger, while the physical 5955 returns finger-present / finger-absent codes on that command.
- [x] Identify a C++ descriptor-serialization mismatch in the reference SIFT implementation; do not blindly copy its enrollment or threshold.
- [x] Add an independent, offline-only OpenCV SIFT comparison experiment and synthetic tests without libfprint/PAM changes or biometric data publication.
- [ ] Use two-layout SIFT experiment on current four private captures, comparing both genuine pairs with all cross-finger controls.
- [ ] Reconstruct reliable native image correction/geometry; verify quality and impostor rejection before discussing fprintd integration.

- [x] Run initial four-capture offline SIFT test: 80×64 yielded 147–244 keypoints and 4–5 RANSAC inliers per pair; 64×80 yielded 1750–2285 keypoints and 5–6 inliers, with **no genuine/impostor separation**.
- [x] Add aggregate-only little-endian 64-versus-80 raw row-boundary probe and five synthetic tests.
- [ ] Investigate candidate row-width seam signals on private original captures before further SIFT tuning; interpret alongside MOH conversion disassembly and user's visual observations.

## Native-driver architecture and fingerprint-enrolment research (11 October 2026)

- [x] Independently verify likely 64 x 80 sensor row geometry: four physical capture sets show 5.48–9.96× median jumps at 64-sample wraps, but only 0.90–1.37× at proposed 80-sample wraps; stride-64 vertical neighbour differences also smaller.
- [x] Inspect OMGrant/ft9201-libfprint's LGPL native Linux WinBio engine bridge, 64 x 80 BIR format, eight-stage repositioned enrollment with duplicate/low-quality retries and private opaque template handling.
- [x] Record key incompatibility: 93a9 uses 96 x 96 native optical hardware, different USB endpoints and FT9348 firmware; do not use those commands or firmware on 5955.
- [x] Document possible modular native implementation in docs/ft9201-engine-porting.md and distinction between vendor matcher and USB capture.
- [ ] Identify engine-adapter DLL and INF engine registration in the matching Windows package for 2808:5955; inspect exports/imports locally, never commit proprietary binaries.
- [ ] Confirm genuine 64 x 80 image correction/8-bit BIR format and vendor engine ABI with offline synthetic diagnostics.
- [ ] Implement private offline multi-sample enrollment / genuine-and-impostor verification; require quality gating and repositioned impressions, not just two-image correlations.
- [ ] Build tested out-of-tree libfprint 5955 transport and matching adapter without replacing distro libraries, enabling logins or altering hardening prematurely.

## Phase: fully native image processing (11 October 2026)

- [x] Identify original signed-word inversion + histogram construction in the recovered native FocalTech 2025 Linux binary; do not include proprietary source/binaries in this repo.
- [x] Implement independent, local-only C11 image-preparation prototype for 5120 little-endian signed-clamped 16-bit samples in an experimental 64 × 80 row arrangement.
- [x] Implement exact-count histogram, documented provisional 1/99-percentile 8-bit conversion, defensive low-contrast handling and aggregate-only metrics.
- [x] Build and pass five **synthetic-only** C tests in a separate container, without USB, biometrics or installing system drivers.
- [ ] Run `make -C native test` on the user's Nobara machine with GCC/Clang, and verify the test output.
- [x] Independently implement the observed five-bin, three-pass histogram smoothing filter with five synthetic tests (not yet integrated with image conversion).
- [x] Implement research-only 256-bin three-pass + 250-bin two-pass histogram pipeline with five synthetic tests; verify branch ratio from FT9362 ELF.
- [x] Add separately testable 200/250 vs 250/250 contrast-cap experiment and five synthetic-only tests; not a verified vendor-equivalent transform.
- [x] Correct earlier fixed 20% contrast cap assumption: the vendor ELF actually performs a sliding-window histogram cutoff search (bins 240 or 190), using a dynamic threshold and fallback.
- [x] Implement an independent, separately tested C cutoff-search module with five synthetic-only tests; keep existing experimental tone map isolated.
- [x] Independently integrate the histogram-selected cutoff into experimental native tone mapping; confirm cutoff-to-output arithmetic through native ELF static disassembly; five synthetic tests and sanitizer checks.
- [x] Validate v3 final scaling arithmetic against static Ubuntu ELF instructions (`0x4f8f1`..`0x4f958`), including the +1e-6 denominator and float-to-integer truncation; six synthetic regression tests under ASan/UBSan.
- [x] Execute the recovered original FT9362 Linux normalizer only in an isolated offline analysis namespace with USB-blocking shim and 8 synthetic patterns; independent model achieves byte-identical output across all 8 cases.
- [x] Add 8 vendor-output synthetic golden vectors to offline C test suite (no proprietary runtime needed on Nobara).
- [ ] Extend parity with additional pattern extremes and settle FocalTech signed-negative handling, sensor calibration, and Windows 5955 MOH image conversion.
- [ ] Reconstruct the full histogram smoothing and tone-map stages from native ELF and cross-check MOH Windows conversion. The current percentile mapping is **our approximation**, not a faithful vendor algorithm.
- [ ] Reconstruct the vendor's image quality and custom feature descriptors on synthetic data before biometric enrollment or verification.
- [ ] Implement and validate real multi-impression template enrollment and genuine/impostor separation before ever considering login integration.

- [x] Reverse-engineer one `FtComputeDescriptors` 256-bit histogram-comparison packing branch (average ×0.125, adjacent-cell threshold ×1.05) and write five synthetic-only tests.
- [ ] Recover histogram construction and sensor-specific branch selection; establish isolated vendor-output parity for extracted descriptors before considering fingerprint matching.

- [x] Trace `FtComputeDescriptors` upstream orientation histogram allocation, ±15 patch, gradient call and trilinear eight-bin interpolation in recovered FT9362 ELF.
- [x] Implement **separate, experimental** native C 8×8×8 histogram and gradient field from synthetic inputs; pass six tests and ASan/UBSan.
- [ ] Recover scale-specific Gaussian lookup, gradient validity rules, algorithm mode and exact mapping of the 512 float bins to the 256-bit final descriptor; test against vendor output.

## First actual-capture image-processing check (private, offline)

- [x] Add stdin/stdout-only native `ft5955_normalize_cli` wrapping our C v3
  16-bit-to-8-bit normalizer; no hardware, vendor code or privilege needed.
- [x] Add `tools/real_capture_eval.py`, using existing private A1/A2/B1/B2
  captures to produce 64×80 and 80×64 grayscale **contact sheets** inside
  gitignored `local-data/native-real-test/` (mode 0700, files 0600).
- [x] Compare six genuine/different-finger image correlations from those
  native-normalized 8-bit frames and report **both margins** without any
  acceptance threshold or claim of verification. Add synthetic CLI/plumbing tests.
- [x] Run the real-capture check on the owner's Nobara system. Review ONLY
  numerical pairwise scores in chat; actual biometric previews stay private.
- [ ] Determine whether the reconstructed normalization improves real ridge
  visibility and genuine/impostor score separation; if not, investigate
  image calibration, physical layout and multi-impression feature extraction
  rather than forcing an identity decision.

Run locally (no new captures):

```bash
git pull --ff-only
make -C native build/ft5955_normalize_cli
python3 tools/real_capture_eval.py
```

Privacy: do not upload or commit actual `.raw` captures, preview images or
feature templates. Keep fprintd, PAM, and the sensor itself untouched.

## Cross-session 5955 fingerprint comparison (pending Nobara run)

- [x] Real-capture test on the 14:55 A1/A2/B1/B2 session produced valid native-normalised 64x80 and 80x64 private previews, with all six scores for each.
- [x] At 64x80, same-finger A=+0.293, B=+0.136; strongest different-finger control=+0.137, margins A=+0.156, B=-0.001. At 80x64, A=+0.231, B=+0.181, strongest different=+0.199, margins A=+0.032, B=-0.018.
- [x] Identify the critical limitation: neither orientation validates B; repeated shifts touch the ±6-pixel boundary. Current image correlation still cannot support authentication.
- [x] Add offline `tools/cross_session_eval.py`, which evaluates 16 early-versus-late pairs across the existing 14:24 and 14:55 sessions, with reversed A/B physical roles.
- [ ] Run `python3 tools/cross_session_eval.py --swapped` after `git pull --ff-only`, using the already-built native v3 executable; evaluate cross-session ranking and boundary shifts with private scans.
- [ ] If across-session genuine/impostor scores overlap, focus on spatial calibration, alignment and complete vendor feature extraction, not threshold tuning or PAM.
