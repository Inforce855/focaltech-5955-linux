# FT5955 working-source consolidation — 17 October 2026

This is the **integration development branch**, not an installation or production release. The intent is to work from GitHub as the authoritative **source of experimental code** without modifying the existing dirty Nobara libfprint working tree.

## GitHub layout: what is current vs historical

| Path | Purpose | Status |
| --- | --- | --- |
| `driver/live-snapshot-2026-10-16/libfprint/drivers/` | **Exact then-live 13 C/header FT5955 driver files** | Preserved with per-file SHA-256; rebuilt and USB Claim/Release tested on 17 October |
| `driver/live-snapshot-2026-10-16/patches/local-libfprint-changes.patch` | Local modifications to core libfprint driver registration and Meson | Applied successfully to the pinned libfprint source; reproduces the then-live main driver exactly |
| `driver/live-snapshot-2026-10-16/engine/` | Current research MOH gateway sources | Preserved source only; proprietary runtime engine not imported or publicly redistributed |
| `tools/verify_ft5955_rebuild.py` | Active isolated rebuild + optional strictly Claim-only device test | `--build` PASS; `--claim-only` PASS on Nobara using the GitHub-built shared library |
| `experiments/private-fprintd/ft5955_claim_only_v097.c` and `.sh` | Dedicated private-bus GetDevices/Claim/Release client/launcher | Hardware PASS, no biometric operation |
| `experiments/private-fprintd/ft5955_private_enroll_v096.[cs]h` | Latest **controlled saved-template baseline** research harness | Brought forward unchanged from `feature/ft5955-private-fprintd-v096` on this branch; previous hardware run matched saved print both before and after daemon restart, with one genuine NO_MATCH before restart |
| `experiments/private-fprintd/ft5955_private_polkit_v095.c` | Minimal, non-root **private-bus-only** PolicyKit helper | Same file on source-history and private-fprintd branches; not a system permission replacement |
| `research/source-history/` | 135 versioned files from historical archives, plus related preserved research sources | **Reference-only**; no old installers/repair scripts should be run against the working checkout |
| `docs/status-2026-10-16.md`, `docs/roadmap.md` | Full experiments and next steps | Reconciled to the latest private-fprintd branch, while retaining historical records |

The snapshot directory deliberately retains the date in its name as an **immutable build input**, not because a newer experimental source must replace it. Avoid copying its C files into another parallel “current” directory. The active build script consumes this exact snapshot, so there is **one selected build source** and versioned archives remain separate. Never delete historical versions to make the repo appear cleaner.

## What has actually been verified

- **16 October 2026:** Using the live private driver, the user completed physical 12-stage enrolment and deliberate fingerprint verification through the isolated private fprintd. Both different-finger rejection controls passed in some sessions; intermittent genuine NO_MATCH also occurred. A controlled saved-print roundtrip matched a saved print **before and after** a private daemon restart.
- **16 October:** Source from GitHub rebuilt to a new libfprint 1.94.100 shared library: 27 Meson targets and Ninja `109/109`.
- **17 October:** The rebuilt shared library was confirmed in private `fprintd`'s `/proc/PID/maps`, then the real FocalTech `2808:5955` reader was discovered, Claimed and Released. No fingerprint scanning, enrolment or verification was performed.
- **NOT YET:** The newly rebuilt library has not independently performed biometric enrolment/verification. No secure production system login, KDE fingerprint UI integration or complete native matcher has been validated.

The user explicitly accepts a deliberate second press if the first legitimate fingerprint is rejected. This is a **usability tolerance**, not permission to turn `NO_MATCH` into an authentication success, to ignore different-finger checks or to weaken password fallback.

## What still blocks a portable, clean-clone build

The SHA-verified builder uses a **pinned libfprint Git commit** `c8e01dc26cedb2d97779a314a7260f1c33e02bfa`, currently present in `~/Projects/libfprint-ft5955` on the user's Nobara system. Its availability from a fresh external clone has **not** been established. The build can be recreated on this machine even with a dirty worktree because `git archive` reads the commit object, not the working files.

**Next read-only task:** establish the provenance and reachability of that exact base commit. If it is local-only, reconstruct its modifications against an identified public upstream libfprint tag/commit or provide a reviewed reproducible base-patch chain. Do **not** assume a random public libfprint checkout contains our scaffold. Do not publish a full fork or vendor arbitrary upstream source without license/build review.

## Working boundaries

- GitHub consolidation branch: `feature/ft5955-driver-consolidation-20261017`, created from source-history and reconciled with the newer v0.9.6 private-fprintd branch. No force pushes, no branch deletion.
- Live private driver at `~/Projects/libfprint-ft5955` **must remain untouched**; same for the local MOH gateway. Do not run `git clean`, destructive checkout, old installers, `sudo` on experimental launchers, or production fprintd/PAM/KDE modifications.
- **No new fingerprint enrolment.** Future offline source audits and build checks should remain image/template-free. The isolated private test state was disposable; there is no confirmed durable enrolled template for subsequent system login.
- Do not commit biometric images, templates, identity-labelled scans, the vendor DLL, private logs, system credentials, or proprietary binaries.

## Safe next check

After fetching this branch into a **separate checkout**, run the static base-commit audit tool `tools/audit_ft5955_base.py`. It reads only the existing local Git object store, does not access USB or print remote URLs, and does not change the libfprint worktree. Then use its result to decide whether to add a clean-clone rebuild pathway.

Until that source provenance is resolved, our results are **working rebuild from saved GitHub sources on the tested Nobara machine**, not yet universally reproducible driver packaging.
