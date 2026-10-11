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
