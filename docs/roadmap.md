# Development roadmap — FocalTech 2808:5955

**Current as of 14 October 2026.** The longer chronological roadmap has been [archived without deleting its experimental findings](archive/roadmap-research-log-2026-10-14.md). Use [current status](current-status.md) for the confirmed hardware results and known-good workflow.

## Milestone 1 — Hardware communication and image acquisition

**Status: experimental baseline achieved.**

- [x] Identify reader VID:PID `2808:5955`, USB endpoints and observed firmware responses.
- [x] Establish bounded contact/release detection and fresh-touch captures.
- [x] Obtain and render 10,240-byte raw captures and 64×80 processed frames.
- [ ] Stabilise USB error handling, reattachment and recovery for sustained daily use.
- [ ] Separate transport/protocol code from model-specific reader details.

## Milestone 2 — End-to-end enrolment and verification

**Status: enrolment achieved; live verification outstanding.**

- [x] Execute the genuine FocalTech MOH Windows engine through an isolated Linux compatibility bridge.
- [x] Reproduce the required 12-impression enrolment and `UpdateEnrollment` completion.
- [x] Implement mock-empty `QueryByContent` for duplicate checking and temporary `CommitEnrollment`.
- [x] Verify four held-out genuine impressions from saved private captures (4/4 matched).
- [x] Confirm mismatched polarity produces four `WINBIO_E_NO_MATCH` outcomes.
- [x] Complete one live enrolment GUI session with temporary in-memory template creation.
- [x] Add an isolated **two-finger temporary identification test harness** with labelled in-memory templates and fresh-touch verification (**hardware testing pending**).
- [ ] **Live verify** the just-enrolled finger, *before* the temporary template is destroyed.
- [ ] Test a genuinely **different finger** and record accept/reject behaviour across sessions.
- [ ] Measure reliability under repositioning, incomplete contact and repeated touches.
- [ ] Review and harden the isolation boundary, confidential template lifetime and failure behaviour.

## Milestone 3 — Native open-source engine

**Status: image-conversion research underway; matcher not yet complete.**

- [x] Independently implement and test candidate image preparation, histogram/tone and spatial processing components in `native/`.
- [x] Preserve synthetic regression vectors and study the Windows matcher as a temporary reference.
- [ ] Validate exact pixel orientation, preprocessing and normalisation across diverse private captures.
- [ ] Reconstruct or independently implement feature extraction, representation and geometric matching.
- [ ] Establish robust genuine/impostor test procedures, including different-finger and cross-session captures.
- [ ] Choose, document and protect a **native** template format; re-enrol for the new implementation if needed.
- [ ] Remove the proprietary DLL dependency once native verification is independently trustworthy.

## Milestone 4 — Standard Linux fingerprint support

**Status: not started; avoid altering current login.**

- [ ] Implement an auditable and maintainable `libfprint` driver or upstream-compatible integration.
- [ ] Add secure, privileged operations, storage and permissions without wide-open USB access.
- [ ] Test `fprintd-enroll` and `fprintd-verify` without changing system authentication.
- [ ] Evaluate KDE screen-unlock support and then opt-in PAM login/`sudo` authentication.
- [ ] Preserve a functioning password-based recovery path at every step.

## Milestone 5 — Other FocalTech readers

**Status: architectural goal, not confirmed compatibility.**

- [ ] Extract documented USB protocol interfaces and device profiles from `2808:5955`.
- [ ] Compare other VID:PIDs before generalising image and engine behaviour.
- [ ] Explore SPI transport separately where Linux and the actual device architecture permit.
- [ ] Publish reproducible, privacy-respecting bring-up notes and synthetic-only tests.

## Research and test navigation

- [Current evidence and working operation sequence](current-status.md)
- [Tool and test inventory](tool-index.md)
- [Native research notes](../native/README.md)
- [MOH compatibility bridge engineering history](5955-moh-engine-bridge.md)
- [Full original research roadmap (archived)](archive/roadmap-research-log-2026-10-14.md)

This roadmap tracks **capabilities demonstrated**, not a guarantee of login suitability or other-model compatibility.
