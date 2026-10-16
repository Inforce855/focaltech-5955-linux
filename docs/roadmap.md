# FocalTech 2808:5955 — development roadmap

**Updated: 16 October 2026.** This is a concise status-driven roadmap, modelled on the layout introduced on `feature/ft5955-moh-engine-bridge`. Earlier experiments are preserved in the [research roadmap archive](archive/roadmap-research-log-2026-10-16.md). See [current status](status-2026-10-16.md) for what was actually demonstrated.

## 1. Sensor communication — experimental baseline achieved

- [x] USB identity `2808:5955`, endpoints, handshake and readiness understood.
- [x] Finger contact/release and physical image capture demonstrated.
- [x] Primary processed image layout established experimentally as 64 × 80 pixels.
- [ ] Validate sustained use, USB recovery, cancellation and error handling.

## 2. Experimental enrolment/matching — demonstrated, not security-validated

- [x] Build isolated MOH research bridge and RAM-only multi-impression enrolment experiments.
- [x] Demonstrate two-finger identification and limited different-finger controls.
- [ ] Validate repeated sessions, difficult placements and genuine/impostor outcomes with sufficient samples.
- [ ] Review proprietary-engine isolation and template confidentiality.

## 3. Native open-source matching — in progress

- [x] Develop standalone image-conversion and preprocessing experiments and synthetic tests.
- [ ] Complete calibrated image and feature extraction parity or independent implementation.
- [ ] Implement and validate a genuine native matcher, secure template format and cross-session reliability.
- [ ] Remove the proprietary Windows DLL research dependency.

## 4. Standard Linux integration — current priority

- [x] Prototype the FocalTech 5955 as an experimental `libfprint` device driver.
- [x] **14 October:** disposable private `fprintd` recognised and claimed the sensor using private PolicyKit.
- [x] **16 October:** v0.9.6 private D-Bus enrolment/verification test **compiled successfully** (`--check`, no scan).
- [x] **16 October:** confirm USB access failure cause (missing write permission); grant narrowly scoped temporary ACL only on the identified `2808:5955` device node; next non-root `Claim` succeeded. Permanent udev handling pending.
- [x] **16 October:** complete genuine 12-stage private-`fprintd` enrolment: 11 intermediate passes plus `enroll-completed (done=true)` from the physical sensor.
- [x] **16 October:** `/dev/tty` confirmation fix tested successfully on Nobara; complete a new physical enrolment, recover from one `enroll-retry-scan`, and receive `VerifyStatus: verify-match (done=true)` on a fresh touch through private `fprintd`. One positive verification only; not a reliability estimate.
- [ ] Test un-enrolled fingers against the template (negative controls), then repeat genuine verification across varied finger placements.
- [ ] Repeat enrol/verify across separate sessions; confirm consistent positive and negative outcomes.
- [ ] Verify persistent storage and reload behaviour, error propagation and privacy boundaries.
- [ ] Only after sufficient evidence, review optional KDE/PAM integration with password fallback.

**Not ready for production login.** A successful compile or one test match is not authentication assurance.

## 5. Source control and reproducible builds

- [ ] Inventory all local `ft5955-*` source snapshots and compare with GitHub; [issue #3](https://github.com/Inforce855/focaltech-5955-linux/issues/3).
- [ ] Commit/review uncommitted local libfprint driver and gateway code without losing changes.
- [ ] Reconcile earlier MOH development branch with current private-fprintd work.
- [ ] Establish a clean-clone build and test path, keeping biometric data and proprietary binaries out of GitHub.
- [ ] Maintain this roadmap and [dated current status](status-2026-10-16.md) alongside each tested change.

## References

- [v0.9.6 private-fprintd test](../experiments/private-fprintd/README.md)
- [Current status and known local development trees](status-2026-10-16.md)
- [Archived research roadmap](archive/roadmap-research-log-2026-10-16.md)
- [Older MOH bridge branch](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-moh-engine-bridge)

Future support for other FocalTech USB or SPI devices is an **architecture goal**, not proven compatibility.
