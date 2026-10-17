# FocalTech 2808:5955 — Linux fingerprint reader

Experimental `libfprint` driver for USB VID:PID **`2808:5955`**, developed and validated on Nobara Linux. **Not yet suitable for production login/PAM.** The current matching research gateway still depends on an isolated proprietary Windows MOH engine; a fully native Linux matcher is a separate unfinished objective.

## Development state — 17 October 2026

| Milestone | Verified status |
| --- | --- |
| USB handshake, contact detection and raw image acquisition | Demonstrated on the physical reader |
| Private `fprintd` device enumeration and Claim | PASS on real hardware |
| Private `fprintd` 12-stage enrolment + genuine verification | PASS in individual tests; **intermittent genuine false rejections** |
| Different-finger rejection controls | Both passed in controlled tests; security significance remains limited |
| Save, reload and match after private `fprintd` restart | **PASS** in controlled before/after restart test |
| Build the preserved driver directly from GitHub snapshot | **PASS**, libfprint 1.94.100; Ninja `109/109` |
| **Fresh GitHub project clone + fresh upstream libfprint clone + three patches** | **PASS 17 October**, exact upstream `80a4b5ec`, all three patches applied, exact saved driver reconstructed; Meson 27 targets, Ninja `109/109` |
| Private `fprintd` **loads exact rebuilt library**, discovers, Claims and Releases real reader | **PASS 17 October**; no biometric capture |
| **Independent clean-clone binary on real FT5955 USB reader** | **PASS 17 October**; private `fprintd` loaded exact new .so, Discover → Claim → Release; zero biometric operations |
| **Normal Nobara system `fprintd` loads our driver and discovers reader** | **PASS 17 October**; verified experimental `.so` mapped by PID 11201; system `GetDevices` lists device; no biometric operations |
| **Reversible service override and rollback** | **PASS 17 October**; experimental `/opt` library and local override removed, original packaged files preserved |
| Production system `fprintd`, KDE fingerprint UI, PAM login | **Not enabled or security validated** |
| Fully native open-source fingerprint matcher | **Not implemented** |

The current development priority is **offline reliability/security review and private error-recovery tests**, followed by carefully controlled, reversible system integration. The user explicitly requested **no further fingerprint enrolments** during these stages. The existing private test templates were stored only in disposable RAM storage, so do not assume durable fingerprints are enrolled for the normal operating system.

## Which files are current?

- **Driver build source:** [`driver/live-snapshot-2026-10-16/`](driver/live-snapshot-2026-10-16/README.md) — 13 SHA-verified driver/header files, the corresponding tracked libfprint/Meson patch and the preserved experimental gateway source. Its dated directory is intentionally **immutable** and is the input used by the tested rebuild tool.
- **Rebuild + Claim-only test:** [`tools/verify_ft5955_rebuild.py`](tools/verify_ft5955_rebuild.py) — temporary-source build; hardware Claim-only mode uses an independent client that has **no enrolment or verification methods**.
- **Current private test harness:** [`experiments/private-fprintd/`](experiments/private-fprintd/README.md) — consolidated from the newest `feature/ft5955-private-fprintd-v096` version, including its successful saved-template baseline test. Historical scripts are retained for reference, not proposed as production tools.
- **Older source research:** [`research/source-history/`](research/source-history/) — deliberately preserved; **do not run historical installers or repair scripts against the active working checkout**.

[Completed clean-clone reconstruction and branch consolidation](docs/consolidation-2026-10-17.md) · [17 October hardware rebuild/Claim report](docs/rebuild-ft5955-without-enrolment.md) · [Detailed status](docs/status-2026-10-16.md) · [Roadmap](docs/roadmap.md)

## Clean-build path — source history now preserved

The libfprint `v1.94.100` tag locally resolves **exactly** to the commit before our first FocalTech driver change. The complete initial C/Meson scaffold patch (2,474 bytes) and subsequent USB-descriptor patch (1,449 bytes) have both been reviewed, SHA-256 verified, and saved in GitHub. Combined with the existing working-driver patch and 13 driver/header sources, the source reconstruction chain is now preserved.

The new [`tools/verify_ft5955_clean_clone.py`](tools/verify_ft5955_clean_clone.py) is intended to **clone an ordinary upstream libfprint release from the network**, apply our three recorded patches in a disposable temporary directory, compare the result against the verified working driver, and compile it there. It does **not** use the dirty `~/Projects/libfprint-ft5955` working checkout. Default invocation is source preflight only; `--build` adds network clone and compilation without sensor access; `--claim-only` separately opts into the isolated USB Discover/Claim/Release test, never enrolment.

**State: PASS on Nobara (17 October 2026).** The user cloned this project afresh, the builder independently cloned the upstream libfprint `v1.94.100` source at **exactly** `80a4b5ec612892c5c056c48dddaa561452cf37ec`, applied all three reviewed patches, reproduced the byte-identical main FocalTech driver from the saved snapshot, and compiled **109/109** steps with **27 Meson targets**. The disposable source and binary were removed; the original live driver/system fprintd/PAM were unchanged. Optional tests were skipped due to disabled introspection and missing dependencies; compilation success is **not** a full test-suite PASS. The log's Git annotated-tag warning and detached HEAD were nonfatal; the actual checked-out commit was verified. **The independent fresh-clone binary has now ALSO passed private real-device GetDevices/Claim/Release (17 October), without a fingerprint capture.** See the [full verified test record](docs/independent-hardware-pass-2026-10-17.md).

The separate test checkout is now confirmed at `~/Projects/ft5955-independent-build-check`; no further clone or checkout is necessary. The independent rebuild's private `--claim-only` run has now passed: it rebuilt in `/tmp`, loaded the exact rebuilt library in private fprintd, discovered, opened and closed the physical FT5955 reader, and removed its temporary test state. The first attempt hit a **USB node permission error** (not a build failure); a user-specific temporary ACL on the exact USB node allowed the successful retry. The manual ACL was **not** undone by the build's cleanup; do not assume a permanent USB permissions solution. It does not install or enable system authentication. No more historical Git archaeology is needed.

[Complete independent build + hardware PASS](docs/independent-hardware-pass-2026-10-17.md) · [Consolidation and audit record](docs/consolidation-2026-10-17.md)

## Reversible Nobara system trial — activation and rollback verified

The independent rebuilt FocalTech library has already passed private physical Discover/Claim/Release. The [read-only system preflight](tools/preflight_ft5955_system_trial.sh) also **PASSED on Nobara 44**: installed `fprintd 1.94.5-5.fc44`, `libfprint 1.94.100-1.fc44`, inactive static service, no local drop-in or `fprintd-pam`, existing USB device allowance and standard systemd sandbox. **The subsequent first installation trial PASSED and was explicitly rolled back. There is no active system-trial installation now.**

The staged trial uses the existing clean builder's new `--stage` mode to save a verified user-owned copy, then [a separate opt-in activation/rollback script](tools/manage_ft5955_system_trial.sh) to copy it to a dedicated root-owned `/opt/ft5955-system-trial` directory, add a narrowly scoped service override, verify loaded `.so` in `/proc/PID/maps`, and call only `GetDevices` on the real system bus. Neither the package library nor PAM is replaced. [Detailed trial and rollback plan](docs/reversible-system-trial-plan.md). **Both user-only `--stage` and privileged `--activate`/`--rollback` passed on Nobara 44.** The temporary system `fprintd` PID 11201 mapped the exact installed trial library (SHA-256 `003ed7e6d53109ad355b653f3b5a9a6cfb33c99e150ae5e58ed7f6ff41fd7d4e`) and normal `GetDevices` returned `/net/reactivated/Fprint/Device/0`. The user then ran rollback successfully, removing the override and `/opt` trial binary. The original packaged libfprint/fprintd were untouched. The staged user-only source artifact may remain. [Detailed activation/rollback result](docs/system-fprintd-install-rollback-pass-2026-10-17.md). **This is a device-discovery success, not normal-service Claim/enrolment/authentication validation.**

**Initial system trial allows device discovery/Claim only.** It does not enable fingerprint enrolment, biometric matching, KDE login, PAM edits or experimental MOH engine execution as root. The historical 14 October reject/cancel/reopen tests already passed, and physical disconnection of the power-button sensor is not a prerequisite.

## MOH gateway isolation toward KDE integration — source-only progress

The normal Nobara `fprintd` loads our driver successfully, but biometric operations remain off in the system trial. The experimental MOH `engine_gateway.py` **refuses root**, while the real `fprintd` service runs as root and uses `ProtectHome=yes`. Do not turn off these protections to force enrolment.

[Experimental local AF_UNIX broker/stdio relay](tools/ft5955_engine_broker.py) is now in GitHub, with a [completely synthetic, non-root test](tools/test_ft5955_engine_broker_synthetic.py) that **PASSED GitHub Actions on 17 October 2026** ([run 39024071118](https://github.com/Inforce855/focaltech-5955-linux/actions/runs/39024071118)). [Dedicated non-root broker systemd unit and socket templates](docs/nonroot-moh-broker-prototype-2026-10-17.md) are **source-only; nothing was enabled or installed**. This test proves byte-stream transport through separate processes only, **not** biometric matching or KDE authentication.

**17 October runner audit completed:** the real local MOH launcher was shared and reviewed. It includes a 110-import audit, pinned SHA-256 copy check, a 20-minute bubblewrap sandbox and source-tree-based compilation; it **defaults to** `/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll` and enables the experimental `FT5955_ALLOW_UNVERIFIED_ATTACH` compile flag. The DLL's current installation and hash **must still be checked**, and the service-specific bwrap/user-namespace behaviour is untested. These flags do not establish security-grade login. Next run [the new non-root read-only relocation audit](tools/audit_ft5955_moh_relocation.py) (syntax independently checked in [GitHub Actions](https://github.com/Inforce855/focaltech-5955-linux/actions/runs/39024520925)); this does not run vendor binaries, use USB, enrol or change login. [Full runner findings](docs/nonroot-moh-broker-prototype-2026-10-17.md). The long-term aim remains replacing the Windows engine with native Linux matching.

## Security and scope

- This is a **research implementation**; successful matching and two negative controls do not demonstrate an acceptable false-accept rate or protection against spoofing.
- Existing false rejections may come from positioning, first-image capture or matching; the user accepts a second deliberate real scan. A terminal `verify-no-match` must **never** be treated as success or silently bypassed.
- Never upload biometric samples, real templates, the proprietary MOH binary, private identification logs or credentials.
- Keep the local `~/Projects/libfprint-ft5955` worktree and `~/Projects/ft5955-driver-integration-v0.8` gateway intact. Avoid `git clean`, `git reset --hard`, experimental installers on live trees and changes to system `fprintd`, PAM or KDE login.
- KDE's built-in Users fingerprint control and [COSMIC Utils Enroll](https://github.com/cosmic-utils/enroll) are **potential GUI front ends** once system integration is safe; neither is a substitute for the driver or security testing.

This branch consolidates development work **without deleting either original GitHub branch or any local source**.
