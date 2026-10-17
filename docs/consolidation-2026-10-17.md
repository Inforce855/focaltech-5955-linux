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

## Pinned-base provenance audit — 17 October 2026 (real Nobara result)

The user ran the **read-only** `tools/audit_ft5955_base.py` directly from GitHub on their existing Nobara development machine. The terminal returned:

```text
PINNED_LIBFPRINT_COMMIT: c8e01dc26cedb2d97779a314a7260f1c33e02bfa
PARENT_COUNT: 1
PARENT_1: 68696e04a88efbecd5dd79cebf05b8ef013c51d8
BASE_CONTAINS_LIBFPRINT_MESON_BUILD: YES
BASE_CONTAINS_LIBFPRINT_DRIVERS_FOCALTECH_5955_C: YES
LOCAL_BRANCHES_CONTAINING_BASE: 1
REMOTE_TRACKING_REFS_CONTAINING_BASE: 0
TAGS_CONTAINING_BASE: 0
CONFIGURED_REMOTE_COUNT: 1
BASE_COMMIT_CHANGED_DRIVER_SCAFFOLD: YES
PASS: audit read Git metadata only; no changes or sensor operations.
```

**Conclusion:** the pinned base commit is accessible from one local Git branch and introduced or modified the FocalTech scaffold; no *locally fetched* remote-tracking branch or tag contains that commit. This strongly suggests a local development commit, but **does not prove that the commit or its parent is unavailable from the upstream remote**. The original build remains reproducible on the user's machine but is not yet verified from a network-clean clone.

### Next source-only check: identify the entire parent-to-base delta

A new reviewed-scope inspector [`tools/inspect_ft5955_base_delta.py`](../tools/inspect_ft5955_base_delta.py) is now committed. It verifies both SHA-1 Git commit objects and their parent relation, prints exactly which paths changed in the scaffold commit, checks for binary/symlink/oversize content, and outputs the prospective text patch size and SHA-256. **By default it reads Git objects only and writes nothing.** It expects changes to be limited to:

- `meson.build`
- `libfprint/meson.build`
- `libfprint/drivers/focaltech_5955.c`

If there are other changes, unsupported file modes, or a non-text delta, the tool **stops** rather than silently excluding them. An optional explicit `--export /absolute/path.patch` writes a reviewable, private-permissions text-only diff outside the active trees; **do not publish any patch without first inspecting its contents**. A patch export is not run by default.

No biometric scan, enrolment, driver installation, system fprintd/PAM change, Git fetch, remote URL output or modification of the local working tree is involved.

### Confirmed parent-to-base scaffold diff — 17 October 2026

The user ran `tools/inspect_ft5955_base_delta.py` read-only on Nobara. It **PASSED** with the exact parent `68696e04a88efbecd5dd79cebf05b8ef013c51d8` and base `c8e01dc26cedb2d97779a314a7260f1c33e02bfa`. Its **entire** changed-path set consisted of just **one modified tracked source**: `libfprint/drivers/focaltech_5955.c` (`M`). No `meson.build` files changed *in this one commit*. The exported candidate text patch was measured (but **not exported**) at **1,449 bytes**, SHA-256 `df8af5a8ac10b716266bb8bdc1107a74c4714079e506a083b2579efa4c5d44f9`. Source patch text itself has **not yet been reviewed or committed to GitHub**. The inspection did not change files, access USB, or perform biometric actions.

**Interpretation:** The immediate parent already had the driver scaffold and Meson registration that appear in the pinned base (as the diff contains no Meson edits), so preserving this one small C patch *alone* does not create a portable build from a vanilla upstream checkout. A second dependency remains: determining how the **parent** obtained its scaffold/Meson additions, and whether it descends from a fetchable public upstream commit. No remote availability claim is made.

**COMPLETED: exact patch reviewed and preserved.** The user provided the full parent-to-base source diff; its code only adds a standard USB GET_DESCRIPTOR validation and reports success or a protocol error, with no fingerprint capture. The reconstructed patch was verified against the audited 1,449-byte length **and** SHA-256 `df8af5a8ac10b716266bb8bdc1107a74c4714079e506a083b2579efa4c5d44f9`, then committed unchanged as [parent-to-base-usb-descriptor.patch](../driver/live-snapshot-2026-10-16/patches/parent-to-base-usb-descriptor.patch). The existing separately recorded later working-driver patch and its SHA-verified source files are unchanged. **Next:** identify the parent commit's earlier scaffold/Meson introduction and a truly available upstream ancestor, then exercise a clean-clone reconstruction. Then inspect the parent ancestry/registration additions against its upstream ancestor; prepare a full patch chain and independent clean-clone build. Existing full build and physical Claim/Release PASS remain valid.

## What still blocks a portable, clean-clone build

The SHA-verified builder uses a **pinned libfprint Git commit** `c8e01dc26cedb2d97779a314a7260f1c33e02bfa`, currently present in `~/Projects/libfprint-ft5955` on the user's Nobara system. Its availability from a fresh external clone has **not** been established. The build can be recreated on this machine even with a dirty worktree because `git archive` reads the commit object, not the working files.

**Next read-only task:** review and preserve the exact single-source patch, then identify the parent commit's scaffold/Meson ancestry and determine whether an upstream ancestor is fetchable. The previous read-only Git provenance audit is complete. If it is local-only, reconstruct its modifications against an identified public upstream libfprint tag/commit or provide a reviewed reproducible base-patch chain. Do **not** assume a random public libfprint checkout contains our scaffold. Do not publish a full fork or vendor arbitrary upstream source without license/build review.

## Working boundaries

- GitHub consolidation branch: `feature/ft5955-driver-consolidation-20261017`, created from source-history and reconciled with the newer v0.9.6 private-fprintd branch. No force pushes, no branch deletion.
- Live private driver at `~/Projects/libfprint-ft5955` **must remain untouched**; same for the local MOH gateway. Do not run `git clean`, destructive checkout, old installers, `sudo` on experimental launchers, or production fprintd/PAM/KDE modifications.
- **No new fingerprint enrolment.** Future offline source audits and build checks should remain image/template-free. The isolated private test state was disposable; there is no confirmed durable enrolled template for subsequent system login.
- Do not commit biometric images, templates, identity-labelled scans, the vendor DLL, private logs, system credentials, or proprietary binaries.

## Safe next check

The scaffold delta inventory is complete: one source file, 1,449-byte patch, checksum above. Next, inspect the complete text of that patch before preserving it on GitHub, then investigate the parent scaffold/Meson chain. This is source-only work; no biometric or system-auth operations.

Until that source provenance is resolved, our results are **working rebuild from saved GitHub sources on the tested Nobara machine**, not yet universally reproducible driver packaging.
