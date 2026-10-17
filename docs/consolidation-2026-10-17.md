# FT5955 working-source consolidation — 17 October 2026

This is the **integration development branch**, not an installation or production release. The intent is to work from GitHub as the authoritative **source of experimental code** without modifying the existing dirty Nobara libfprint working tree.

## Clean upstream-clone rebuild — hardware-free PASS on Nobara (17 October 2026)

**Independently verified from the user's terminal output.** The user created a separate clean checkout `~/Projects/ft5955-independent-build-check` of this feature branch (GitHub clone reported 285 objects) and ran `tools/verify_ft5955_clean_clone.py --build`. The new builder:

- verified the SHA-256 manifest for the saved FocalTech driver plus both historical source patches;
- independently fetched official libfprint `v1.94.100` from `https://gitlab.freedesktop.org/libfprint/libfprint.git`, without using `~/Projects/libfprint-ft5955`, and verified the checked-out `HEAD` equals exact upstream commit `80a4b5ec612892c5c056c48dddaa561452cf37ec`;
- successfully applied, in order, the **initial discovery scaffold**, **USB descriptor support**, and **complete live driver/Meson** patches;
- checked the final reconstructed main driver file byte-for-byte against the captured GitHub snapshot, and copied the other 12 verified driver/header files;
- configured Meson **27 build targets** for libfprint 1.94.100 with only the `focaltech_5955` driver, `doc=false`, `introspection=false`;
- compiled successfully: `[109/109] Linking target tests/test-fpi-device`; emitted `PASS: CLEAN upstream clone + 3 GitHub patches built independently`;
- removed disposable `/tmp/ft5955-rebuild-*` source/build artifacts, without changing the existing live checkout, installed system fprintd or PAM.

The upstream clone showed an **annotated release tag** warning, followed by detached-HEAD checkout of `80a4b5ec`. That warning was nonfatal, and the builder independently checked the exact commit. Meson reported optional test dependencies absent and skipped driver tests without introspection. **109/109 proves source compilation; it is not a passing test-suite report.**

**What this closes:** the local-only Git-object build dependency. The full saved active source is now reconstructable from the public upstream release plus files committed to this project, on the user's Nobara environment. This does not prove cross-distribution packaging or reproducible machine-bit-for-bit binaries.

**What remains:** the **new clean-clone-compiled** library has **not yet been tested against USB hardware**; the earlier private Claim/Release PASS used the prior GitHub-rebuilt library. No biometric enrolment, recognition, saved-template check, KDE GUI, system installation or authentication is validated by this new compile.

**Next isolated milestone:** from the existing clean GitHub checkout, execute `python3 "$HOME/Projects/ft5955-independent-build-check/tools/verify_ft5955_clean_clone.py" --claim-only`. This rebuilds privately and runs only device discovery, Claim and Release, with no fingerprint scan/enrolment and no PAM, system fprintd or KDE changes. A USB permission blocker can occur after reboot and should be diagnosed without blanket permission changes.

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

## Initial scaffold ancestry identified — 17 October 2026

The user inspected libfprint Git history **read-only** after preserving the USB descriptor patch:

```text
ORIGINAL SCAFFOLD ADDITION:
68696e04a88efbecd5dd79cebf05b8ef013c51d8 Add FocalTech 5955 discovery-only driver
NEAREST LOCAL UPSTREAM TAG:
v1.94.100
PARENT COMMIT:
68696e04a88efbecd5dd79cebf05b8ef013c51d8 80a4b5ec612892c5c056c48dddaa561452cf37ec Add FocalTech 5955 discovery-only driver
```

This establishes an exact first FocalTech commit (`68696e04`) and its immediate pre-FocalTech parent (`80a4b5ec`). The nearest reachable **local** release tag is `v1.94.100`; this alone **does not establish** that `80a4b5ec` equals the tag commit or that the tag is currently obtainable over the network.

The committed [read-only scaffold-origin audit](../tools/audit_ft5955_scaffold_origin.py) checks tag equality/ancestry, lists any intervening upstream modifications, rejects unexpected initial scaffold patch files/modes, and prints the exact diff size and SHA-256. Its optional `--show-patch` prints the full vetted source-only diff in the terminal for review; it does not export, install or modify files. **The new script has not yet been run on Nobara.** After validating the diff, we can preserve that earlier scaffold/Meson patch and reconstruct from an independently fetchable upstream source.

### Initial-scaffold audit result — 17 October 2026

The user ran the read-only ancestry audit on Nobara. **Release tag resolved exactly:** `v1.94.100` points to `80a4b5ec612892c5c056c48dddaa561452cf37ec`, which is the **immediate parent** of first FocalTech scaffold commit `68696e04a88efbecd5dd79cebf05b8ef013c51d8`. No intervening commits (`COMMITS_AFTER_RELEASE_TAG_TO_PARENT: 0`).

The initial scaffold commit changed **three** files:

```text
A libfprint/drivers/focaltech_5955.c
M libfprint/meson.build
M tests/meson.build
```

The first audit run **stopped by design** because our exact-path safety whitelist incorrectly expected `meson.build` at the repository root, rather than the observed `tests/meson.build`. That does **not** indicate a failed libfprint build. The whitelist has now been corrected to precisely those three statuses and paths, with all original commit checks, safe file-mode checks, binary rejection, maximum patch size and read-only operation intact (commit `4cdf4a5`). The corrected audit subsequently **PASSED** (2,474-byte initial patch; SHA-256 recorded in the next section). The original first-failure event remains preserved above for audit history.

**Subsequently completed:** the corrected audit passed and the three-file patch was saved with exact SHA-256 verification. The next test is the separate upstream-clone builder, not another ancestry inspection.

## Initial scaffold PASS and independent-build implementation — 17 October 2026

The user reran the corrected audit successfully. Their local `v1.94.100` tag resolved **exactly** to `80a4b5ec612892c5c056c48dddaa561452cf37ec`, the direct parent of the FocalTech discovery commit `68696e04`. The complete initial scaffold patch changes **only** these three expected paths: adds `libfprint/drivers/focaltech_5955.c`, modifies `libfprint/meson.build`, and modifies `tests/meson.build` (correcting the foreach test-loop unpacking). It was **2,474 bytes** with SHA-256 **`5a4f80b925ad2640689f1748fb175ca0b01650ebb697da8d74743cf7080047cd`**. Full patch content was supplied and reviewed; the two invisible leading Git-diff context spaces were reconstructed and its SHA-256 verified before committing [the exact scaffold patch](../driver/live-snapshot-2026-10-16/patches/upstream-v1.94.100-to-initial-scaffold.patch). Its Git blob SHA was independently checked against the audited bytes.

The complete recorded reconstruction chain is now:

1. Unmodified upstream libfprint release tag `v1.94.100`, expected commit `80a4b5ec`.
2. SHA-verified [initial scaffold patch](../driver/live-snapshot-2026-10-16/patches/upstream-v1.94.100-to-initial-scaffold.patch), original local commit `68696e04`.
3. SHA-verified [USB-descriptor patch](../driver/live-snapshot-2026-10-16/patches/parent-to-base-usb-descriptor.patch), original local commit `c8e01dc`.
4. Existing [working-driver code and Meson patch](../driver/live-snapshot-2026-10-16/README.md), plus all 13 SHA-verified driver/header files.

The new [`tools/verify_ft5955_clean_clone.py`](../tools/verify_ft5955_clean_clone.py) leaves the successful original rebuild path unchanged. It validates the snapshot and **both historical patch hashes**, clones the exact upstream release into a disposable `/tmp/ft5955-rebuild-*` tree, insists `HEAD` equals the expected tag commit, applies the three reviewed patches, verifies the final driver source equals the captured SHA-verified snapshot, layers the remaining driver files, and runs the same Meson/Ninja configuration. Default invocation is read-only manifest preflight; `--build` opts into the network clone and compile, without USB access, enrolment, install, PAM or KDE changes. `--claim-only` additionally enables the previously demonstrated isolated no-enrolment hardware claim harness. All temp files are removed after command completion. **The independent clean-clone build PASSED on Nobara; see the verified result at the top of this document.**

**The network clone of the exact upstream tag and fresh-clone compile have now PASSED on Nobara (17 October 2026).** If the upstream server blocks the Git clone, report that as an availability problem, not a driver-code failure. Do not switch branches or overwrite the existing live driver checkout.

## Historical clean-clone blocker (resolved 17 October 2026)

The SHA-verified builder uses a **pinned libfprint Git commit** `c8e01dc26cedb2d97779a314a7260f1c33e02bfa`, currently present in `~/Projects/libfprint-ft5955` on the user's Nobara system. Its availability from a fresh external clone has **not** been established. The build can be recreated on this machine even with a dirty worktree because `git archive` reads the commit object, not the working files.

**Resolved:** the independent clean-clone `--build` passed on Nobara. The next test uses `--claim-only` to check physical USB Claim without biometric operations. The previous read-only Git provenance audit is complete. If it is local-only, reconstruct its modifications against an identified public upstream libfprint tag/commit or provide a reviewed reproducible base-patch chain. Do **not** assume a random public libfprint checkout contains our scaffold. Do not publish a full fork or vendor arbitrary upstream source without license/build review.

## Working boundaries

- GitHub consolidation branch: `feature/ft5955-driver-consolidation-20261017`, created from source-history and reconciled with the newer v0.9.6 private-fprintd branch. No force pushes, no branch deletion.
- Live private driver at `~/Projects/libfprint-ft5955` **must remain untouched**; same for the local MOH gateway. Do not run `git clean`, destructive checkout, old installers, `sudo` on experimental launchers, or production fprintd/PAM/KDE modifications.
- **No new fingerprint enrolment.** Future offline source audits and build checks should remain image/template-free. The isolated private test state was disposable; there is no confirmed durable enrolled template for subsequent system login.
- Do not commit biometric images, templates, identity-labelled scans, the vendor DLL, private logs, system credentials, or proprietary binaries.

## Safe next check

Both historical patches are preserved and SHA-256 verified, and the original pre-scaffold commit exactly equals the local `v1.94.100` tag. The independent clean-clone builder now has a hardware-free `--build` PASS; the next milestone is its private no-enrolment `--claim-only` mode. This is source-only work; no biometric or system-auth operations.

Source provenance and the external-clone build are resolved for the tested Nobara environment. **No system driver package, fingerprint login, or cross-machine reliability assurance has yet been demonstrated.**
