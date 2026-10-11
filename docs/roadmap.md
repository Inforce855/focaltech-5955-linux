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
- [ ] Verify the handshake on this physical reader.
- [ ] Trace mandatory scan activation, readiness checks and return-to-idle operations before full capture.
- [x] Build and locally test a private offline 16-bit raw-to-PNG converter, with synthetic tests.
- [ ] Build bounded multi-transfer image acquisition; validate the pixel format and save images only in ignored local-data.
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
