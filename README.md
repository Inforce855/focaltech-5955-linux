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
| Private `fprintd` **loads exact rebuilt library**, discovers, Claims and Releases real reader | **PASS 17 October**; no biometric capture |
| Production system `fprintd`, KDE fingerprint UI, PAM login | **Not enabled or security validated** |
| Fully native open-source fingerprint matcher | **Not implemented** |

The current development priority is **source consolidation, clean-clone rebuild, reliability/security review and ultimately reversible system integration**. The user explicitly requested **no further fingerprint enrolments** during these stages. The existing private test templates were stored only in disposable RAM storage, so do not assume durable fingerprints are enrolled for the normal operating system.

## Which files are current?

- **Driver build source:** [`driver/live-snapshot-2026-10-16/`](driver/live-snapshot-2026-10-16/README.md) — 13 SHA-verified driver/header files, the corresponding tracked libfprint/Meson patch and the preserved experimental gateway source. Its dated directory is intentionally **immutable** and is the input used by the tested rebuild tool.
- **Rebuild + Claim-only test:** [`tools/verify_ft5955_rebuild.py`](tools/verify_ft5955_rebuild.py) — temporary-source build; hardware Claim-only mode uses an independent client that has **no enrolment or verification methods**.
- **Current private test harness:** [`experiments/private-fprintd/`](experiments/private-fprintd/README.md) — consolidated from the newest `feature/ft5955-private-fprintd-v096` version, including its successful saved-template baseline test. Historical scripts are retained for reference, not proposed as production tools.
- **Older source research:** [`research/source-history/`](research/source-history/) — deliberately preserved; **do not run historical installers or repair scripts against the active working checkout**.

[Complete branch reconciliation and remaining clean-clone blocker](docs/consolidation-2026-10-17.md) · [17 October hardware rebuild/Claim report](docs/rebuild-ft5955-without-enrolment.md) · [Detailed status](docs/status-2026-10-16.md) · [Roadmap](docs/roadmap.md)

## Clean-build path — source history now preserved

The libfprint `v1.94.100` tag locally resolves **exactly** to the commit before our first FocalTech driver change. The complete initial C/Meson scaffold patch (2,474 bytes) and subsequent USB-descriptor patch (1,449 bytes) have both been reviewed, SHA-256 verified, and saved in GitHub. Combined with the existing working-driver patch and 13 driver/header sources, the source reconstruction chain is now preserved.

The new [`tools/verify_ft5955_clean_clone.py`](tools/verify_ft5955_clean_clone.py) is intended to **clone an ordinary upstream libfprint release from the network**, apply our three recorded patches in a disposable temporary directory, compare the result against the verified working driver, and compile it there. It does **not** use the dirty `~/Projects/libfprint-ft5955` working checkout. Default invocation is source preflight only; `--build` adds network clone and compilation without sensor access; `--claim-only` separately opts into the isolated USB Discover/Claim/Release test, never enrolment.

**State:** the clean-clone builder has been committed, but independent network fetch/compile have **not yet passed on Nobara**. The original pinned-commit rebuild and physical Claim/Release test have already passed and are unchanged.

To keep the user's existing project sources intact, run the new builder from a **separate checkout** of branch `feature/ft5955-driver-consolidation-20261017` when ready for the next source-only test. No more historical Git archaeology is needed.

[Clean-build and audit record](docs/consolidation-2026-10-17.md) · [Previously verified private hardware test](docs/rebuild-ft5955-without-enrolment.md)

## Security and scope

- This is a **research implementation**; successful matching and two negative controls do not demonstrate an acceptable false-accept rate or protection against spoofing.
- Existing false rejections may come from positioning, first-image capture or matching; the user accepts a second deliberate real scan. A terminal `verify-no-match` must **never** be treated as success or silently bypassed.
- Never upload biometric samples, real templates, the proprietary MOH binary, private identification logs or credentials.
- Keep the local `~/Projects/libfprint-ft5955` worktree and `~/Projects/ft5955-driver-integration-v0.8` gateway intact. Avoid `git clean`, `git reset --hard`, experimental installers on live trees and changes to system `fprintd`, PAM or KDE login.
- KDE's built-in Users fingerprint control and [COSMIC Utils Enroll](https://github.com/cosmic-utils/enroll) are **potential GUI front ends** once system integration is safe; neither is a substitute for the driver or security testing.

This branch consolidates development work **without deleting either original GitHub branch or any local source**.
