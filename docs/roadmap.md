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
- [ ] Verify the reply with a finger absent, then (if safe) with a finger resting on the sensor.
- [ ] Establish status-byte meaning from live observations before implementing any polling.
- [ ] Determine whether further initialisation is required for event reporting or imaging.

See [protocol research notes](protocol-research.md).

## Phase 4 — Fingerprint functions

- [ ] Detect finger-present transitions.
- [ ] Determine image-acquisition or on-device matching capabilities.
- [ ] Implement safe enrolment and verification without leaking templates.

## Phase 5 — Linux desktop integration

- [ ] Implement a stable `libfprint` driver or documented alternative.
- [ ] Test through `fprintd` independently of production authentication.
- [ ] Evaluate reliability, privacy and access controls.
- [ ] Optionally enable KDE / PAM integration once proven safe.

## Explicitly out of scope for the initial release

Firmware flashing, guessed USB command bytes, system fingerprint-library replacement and changing login authentication.
