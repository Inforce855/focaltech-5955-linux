# FocalTech 2808:5955 — development roadmap

**Updated: 17 October 2026.** This is a concise status-driven roadmap, modelled on the layout introduced on `feature/ft5955-moh-engine-bridge`. Earlier experiments are preserved in the [research roadmap archive](archive/roadmap-research-log-2026-10-16.md). See [current status](status-2026-10-16.md) for what was actually demonstrated.

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
- [x] **16 October:** first `--controls` hardware run: right-index genuine match, right-middle different-finger no-match, left-index different-finger no-match. The second right-index genuine attempt returned `verify-no-match (done=true)` and the strict initial client exited **FAIL**. User reported possible incomplete sensor placement; cause unconfirmed. One `enroll-retry-scan` was recovered during enrolment.
- [x] **16 October:** bounded-retry controls ran on hardware: one genuine match, two distinct-finger rejections and **three terminal genuine no-matches** when returning to the enrolled finger. Overall control sequence FAIL; no different-finger false matches observed in this limited test.
- [x] **16 October:** subsequent `--controls` run completed **4/4** first-attempt expectations: two enrolled right-index matches, two different-finger `verify-no-match` rejections, and zero genuine no-matches. This shows that negative comparisons do **not invariably** prevent later genuine matches; earlier failed runs remain relevant.
- [ ] **Optional diagnostic on Nobara:** the committed `--diagnose` mode alternates A, A, B, A, C, A to help localise intermittent genuine no-matches. It is not yet hardware-tested and is less urgent than collecting repeatability data.
- [x] **16 October `--roundtrip` physical test: PARTIAL PASS / OVERALL FAIL.** Enrolled fingerprint name appeared in private fprintd both before and after restart with the same RAM state; all three genuine post-restart checks returned terminal `verify-no-match`. Not a successful reusable biometric template. No same-session baseline was run in this test.
- [x] **16 October controlled `--roundtrip`: FULL PASS.** Physical right-index print successfully enrolled and listed; a fresh client on the original private `fprintd` matched the saved template on genuine attempt **2/3** (one preceding terminal genuine `NO_MATCH`); after restarting only private `fprintd` with the same RAM state, another fresh client listed and MATCHED it on the **first** genuine attempt. This disproves *inevitable* restart-induced loss, **not** intermittent failures or security/reliability limitations. No different-finger check in this particular test. See [verified status](status-2026-10-16.md).
- [x] Inspect the **then-live private libfprint driver ↔ MOH gateway** path: committed live-source snapshot confirms FpPrint RAW envelope pack/extract, SHA-256 integrity check, and acknowledgement of MOH template import before scanning. This is source inspection, not byte-level persistence validation.
- [ ] **Usability acceptance (user-confirmed, 16 October):** the built-in reader is awkward to reach and requires stretching; **one genuine `NO_MATCH` followed by a successful second deliberate press is acceptable**. Prioritise predictable manual retry, preserved security/negative controls, and practical integration over eliminating every first-touch rejection. Never silently turn a `NO_MATCH` into a successful login; leave password fallback available.
- [ ] **Lower priority:** investigate intermittent genuine `NO_MATCH` only if retries become inconsistent or excessively frequent; controlled logs may distinguish touch positioning, capture quality and engine return code without publishing biometric samples or templates.
- [ ] Repeat successful before/after daemon restarts across multiple **bounded**, separately documented trials; negative controls and error rates are still insufficient.
- [ ] Repeat enrol/verify across separate sessions; confirm consistent positive and negative outcomes.
- [ ] Verify persistent storage and reload behaviour, error propagation and privacy boundaries.
- [ ] Only after sufficient evidence, review optional KDE/PAM integration with password fallback.
- [ ] **Optional future GUI: [COSMIC Utils Enroll](https://github.com/cosmic-utils/enroll)** ([Flathub](https://flathub.org/apps/org.cosmic_utils.enroll)). Source reviewed 17 October 2026: Rust/libcosmic frontend calls normal `net.reactivated.Fprint` **system-bus** D-Bus methods for user selection, listing prints, Register/`EnrollStart`, Verify/`VerifyStart` and deletion; Flatpak manifest grants system bus access to fprintd, PolicyKit and Accounts. It does **not** add sensor drivers or native matching. Could become a GUI for our reader **only after** safe system fprintd/libfprint integration; it does **not** automatically find the existing isolated private D-Bus test service. COSMIC styling may also work under KDE, but this has **not** been tested on user's Nobara installation. **Do not click Register/Enroll or Delete** in the current no-enrolment phase; no installation or system-auth changes requested.

**Not ready for production login.** A successful compile or one test match is not authentication assurance.

## 5. Source control and reproducible builds

- [x] Recover and inventory the uploaded historical archives; **135 source files** from 16 versioned directories imported to [`feature/ft5955-source-history`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-source-history/research/source-history). Inventory of further *local* snapshots may remain; [issue #3](https://github.com/Inforce855/focaltech-5955-linux/issues/3).
- [x] **Preserve** the then-live private libfprint driver and gateway in commit [`77db7f5`](https://github.com/Inforce855/focaltech-5955-linux/commit/77db7f5): 13 driver/header sources, 3 gateway files, tracked Meson/driver patch and hashes. Original dirty checkout was not modified. **Still needed:** reconcile it into a clean-clone reproducible development build.
- [ ] Reconcile earlier MOH development branch with current private-fprintd work.
- [x] **16 October:** rebuild the preserved live driver source from GitHub in an isolated temporary tree using libfprint 1.94.100 and pinned upstream commit `c8e01dc`; SHA-verified snapshot and recorded Meson patch applied, Meson configured FocalTech-only driver, Ninja finished **109/109 build steps** (27 Meson targets). No enrolment, hardware scan, install or changes to the working driver. [Source-history rebuild proof](https://github.com/Inforce855/focaltech-5955-linux/blob/feature/ft5955-source-history/docs/rebuild-ft5955-without-enrolment.md).
- [x] **17 October:** GitHub-rebuilt library was loaded by a fresh disposable private `fprintd`, confirmed by `/proc/PID/maps`, and the physical `2808:5955` reader was **discovered, Claimed and Released**. Dedicated Claim-only client had no enrol/verify code; hardware test PASS, with source build 109/109 steps and successful cleanup. [Verified report](https://github.com/Inforce855/focaltech-5955-linux/blob/feature/ft5955-source-history/docs/rebuild-ft5955-without-enrolment.md).
- [ ] Establish independent clean-clone build (the successful rebuild still uses the pinned upstream libfprint commit from the user's local Git object store), complete an offline regression review, and prepare any system integration only after explicit review, safe rollback and password fallback. **User requests no further enrolments.**
- [ ] Maintain this roadmap and [dated current status](status-2026-10-16.md) alongside each tested change.

## References

- [v0.9.6 private-fprintd test](../experiments/private-fprintd/README.md)
- [Current status and known local development trees](status-2026-10-16.md)
- [Archived research roadmap](archive/roadmap-research-log-2026-10-16.md)
- [Older MOH bridge branch](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-moh-engine-bridge)

Future support for other FocalTech USB or SPI devices is an **architecture goal**, not proven compatibility.
