# Development roadmap

## Phase 1 — USB identification (complete)

- [x] Identify USB device ID `2808:5955`.
- [x] Record the interface and bulk endpoints.
- [x] Check installed Nobara `fprintd` / `libfprint` support.
- [x] Identify the matching MOH Windows driver package.

## Phase 2 — Safe diagnostic application

- [x] Add a descriptor-only diagnostic command.
- [x] Add an explicitly opted-in, timed IN-only listener.
- [ ] Test the diagnostic app on the actual Nobara system.
- [ ] Record non-sensitive observations and permission behaviour.

## Phase 3 — Protocol research

- [ ] Independently establish message framing and checksum/status handling.
- [ ] If needed, inspect Windows USB traffic from user-owned hardware.
- [ ] Validate harmless, read-only commands before adding any USB OUT support.

## Phase 4 — Fingerprint functions

- [ ] Detect finger-present transitions.
- [ ] Determine whether image acquisition or on-device matching is available.
- [ ] Implement safe enrolment and verification without leaking templates.

## Phase 5 — Linux desktop integration

- [ ] Implement a stable `libfprint` driver or documented alternative.
- [ ] Test through `fprintd` independently of production authentication.
- [ ] Evaluate reliability, privacy and access controls.
- [ ] Optionally enable KDE / PAM integration once proven safe.

## Explicitly out of scope for the initial release

Firmware flashing, guessed USB command bytes, system fingerprint-library replacement and changing login authentication.
