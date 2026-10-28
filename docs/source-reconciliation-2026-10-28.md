# FocalTech 5955 — source and deployment reconciliation checkpoint

**Audit date:** 28 October 2026. **Status:** HISTORICAL SOURCE AUDIT VERIFIED; relay provenance and security/release reconciliation still incomplete. **Do not delete FocalTech research branches, reset dirty worktrees, reinstall libfprint or change PAM/systemd.** This is a source/deployment audit, not approval for production biometric authentication.

## Verified follow-up — 28 October 2026 (supersedes earlier open source-inventory questions)

The owner compared local archive regular-file contents using Git-style blob hashes against the *current* GitHub `main` tree `ea86740fbe9d04c9a209f49b8c64186fae8729a3`. **All 135 source files in 16 downloaded archives matched the corresponding committed historical source.** The only two archive members not in GitHub were generated `__pycache__/*.cpython-313.pyc` files in `ft5955-moh-libfprint-v0.6.1.tar.gz`, not missing human-authored source. The separate `fix_focaltech_5955_scaffold.py` also matched its GitHub blob exactly (local SHA-256 `92cb5358aaad44044b4dc3f9469637598a1e470f2bf39253f3868eaf0a70eedb`). The three additional archives were `focaltech-nbis-one-touch.tar.gz` (5/5), `focaltech-5955-libfprint-scale-fix.tar.gz` (3/3) and `focaltech-5955-live-libfprint.tar.gz` (5/5). The vendor archive was **not** part of this source equivalence claim.

Of the **11 untracked files in local main**, 8 matched existing GitHub historical blobs exactly; the remaining 3 (`build_isolated_libfprint.sh`, `build_nbis_diagnostic.sh`, `run_isolated_enroll.sh`) differed **only by correcting default directories** from `~/Projects/...` to `~/Projects/Fingerprint-FT5955/...`. The **3 modified MOH worktree scripts** and **6 modified source-history worktree files** likewise contained **only local path-default corrections**; no algorithm or driver-logic change was identified in these displayed diffs. Local `.gitignore` adds `.aider*` only. **All local changes and all worktrees remain untouched**: source provenance is not permission to reset/clean them. The private `moh-attach-disassembly.txt` (30,360 bytes; local SHA-256 `7072f6470f5c3b6aeddf49d08b51db414b12fbcc4e939057b95e61536143cc43`) has only been inventoried, not content-reviewed or uploaded.

**Read-only live deployment inventory:** `fprintd.service` still runs `/usr/libexec/fprintd` with effective `LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib`, `FT5955_EXPERIMENTAL_ENABLE=1`, `FT5955_ENGINE_GATEWAY=/opt/ft5955-dev/ft5955_dev_relay.py`; drop-ins are `90-ft5955-system-trial.conf` and `95-ft5955-moh-dev-gateway.conf`, plus the distribution timeout drop-in. `ft5955-engine-dev.socket` is **enabled and active**, while the socket-activated `ft5955-engine-dev.service` was **static/inactive** at inspection (not by itself a malfunction). The libfprint symlink resolves to `/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0`.

- Installed libfprint SHA-256: **`02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`**, exactly the historically documented **known-good original verify-only library**, restored after the unsuccessful identification v2 trial.
- Installed `/opt/ft5955-dev/ft5955_engine_broker.py`: local SHA-256 `5f6925c5cd7a1cf1aa9acf780b674dbb44379d9d190ac0d42b44783be57ce0e5`; owner ran `git hash-object --no-filters` on the installed file and obtained **Git blob `6fa2dcf7ece70cabab19b9e2825f2255fa437a3f`**, *exactly matching* committed `tools/ft5955_engine_broker.py` with the earlier tested one-second cleanup fix. Git blob SHA-1 and file SHA-256 are different checksum schemes, not conflicting revisions.
- Installed `/opt/ft5955-dev/ft5955_dev_relay.py` SHA-256: `a86c8a50e531876b30a8d7bad6a4661bcae5e2cbc894d4b254608d205c26f3e4`; its exact committed/source provenance has **not yet been established**.
- These checks prove **files and effective service configuration as inspected**, not a new running-process mapping, a post-check hardware test or production security certification. Do not repeat already successful baseline authentication tests without evidence of regression.

**REMAINING:** reconcile the installed development relay and relevant privileged service/template trust boundary; preserve named authselect rollback and password fallback; keep the reverted multi-template `identify` experiment distinct from the known-good verify-only library; plan maintained non-`dev` release/rollback only after source/security checks. **GitHub branch pruning remains on hold** pending owner approval and handling of the still-dirty local worktrees. Earlier "source members not yet compared", "v0.6.1 missing source" and "installed hash unknown" statements below are dated pre-verification observations superseded by this section.

## Why this checkpoint exists

A source review found that, during 14 October development, several intermediate designs were exchanged as downloadable archives or installable patches rather than consistently committed as individually reviewable GitHub source changes. The owner still retains working source trees, several dirty Git worktrees, original downloads and older ChatGPT conversation exports.

Sources reviewed: owner-provided *read-only* `git worktree list`, `git branch -vv` and `git status -sb` output on 28 October; the user's historical `chat(1).html` conversation archive (October 11–18 sessions); and two 20 October Markdown session exports relating to USB timing/relay latency and multi-finger identification. **The complete private chat archive and unexamined downloaded packages have not been uploaded to this public repository.** The session exports explicitly flag earlier inaccessible transcript portions; do not claim they contain every experiment.

## Local source/worktree findings (28 October)

The owner's local repository root had these statuses when inspected:

| Checkout | Checked-out branch and commit | Changes observed — preserve |
| --- | --- | --- |
| Main source worktree | `main` at `a8a5430` | Modified `.gitignore` and 11 untracked documentation, C, Python and shell files |
| MOH worktree | `feature/ft5955-moh-engine-bridge` at `ae6d25f` | Three modified existing tools/scripts (v0.9.2–v0.9.4 testing) |
| Source-history worktree | `feature/ft5955-source-history` at `c98bce2` | Six modified existing driver/engine/test-history files |

Both main and MOH locally tracked branches were reported **13 behind their remote-tracking branches** at the time of the owner's last local fetch. Source-history had no ahead/behind indication. These counts are **local tracking observations** and do not prove the installed binary matches any checkout. No `git pull`, reset, clean or worktree removal was attempted.

### Source files absent at the same path from all nine current remote branch tips

The eleven files listed as untracked in the local main worktree were compared with the recursive Git trees of all nine remote branches (28 October); **none was found under the corresponding path on any branch tip**:

```text
docs/LIVE_LIBFPRINT_BRIDGE.md
docs/NBIS_ONE_TOUCH.md
docs/README-scale-test.txt
native/ft5955_nbis_probe.c
tests/test_live_libfprint_bridge.py
tests/test_nbis_one_touch_diagnostic.py
tools/build_isolated_libfprint.sh
tools/build_nbis_diagnostic.sh
tools/live_libfprint_bridge.py
tools/nbis_one_touch_diagnostic.py
tools/run_isolated_enroll.sh
```

**Qualification:** Their functionality may exist in other remote files under different names, older Git history, archives or installed binaries. Their contents and equivalence have **not** yet been reviewed. Do not blindly stage/commit files or trust their safety merely because they exist locally.

### Download and package provenance to reconcile

The October 14 chat history explicitly mentions the following packages or extraction trees:

```text
ft5955-moh-ipc-v0.1
ft5955-moh-ipc-v0.2
ft5955-moh-libfprint-v0.6
ft5955-driver-actions-v0.7
ft5955-driver-integration-v0.8
ft5955-native-validation-v0.9.1
ft5955-v094-source
```

These are **historical package names**, not a list of verified production releases. The transcript includes both passing offline smoke tests and failed or incomplete C build/integration attempts. Some packages were on GitHub or later copied into feature branches, and others were downloaded locally; **the package contents have not been byte-compared against GitHub in this audit**. Do not add opaque archives, personal conversation exports, raw fingerprint images, templates or proprietary DLLs to GitHub.

## Recovered archive inventory — owner read-only listing, 28 October 2026

A filesystem `find` at `~/Downloads` and `~/Projects/Fingerprint-FT5955` (max depth 3, matching FT5955-related archives) found **15 archive files under Downloads** and a second copy/path of **native-validation-v0.9.1** inside the MOH-test checkout. This establishes *presence and pathname only*; SHA-256 hashes, member manifests, extraction safety, archive duplicates and equivalence to repository commits are **not yet verified**.

```text
~/Downloads/7_Fingerprint-module.zip
~/Downloads/ft5955-driver-actions-v0.7.tar.gz
~/Downloads/ft5955-driver-integration-v0.8.tar.gz
~/Downloads/ft5955-driver-sources.tar.gz
~/Downloads/ft5955-moh-ipc-v0.1.tar.gz
~/Downloads/ft5955-moh-ipc-v0.2.tar.gz
~/Downloads/ft5955-moh-ipc-v0.3.tar.gz
~/Downloads/ft5955-moh-libfprint-v0.6.1.tar.gz
~/Downloads/ft5955-moh-libfprint-v0.6.tar.gz
~/Downloads/ft5955-moh-print-v0.5.tar.gz
~/Downloads/ft5955-moh-template-v0.4.tar.gz
~/Downloads/ft5955-native-validation-v0.9.1.tar.gz
~/Downloads/ft5955-native-validation-v0.9.tar.gz
~/Downloads/ft5955-v094-source (1).tar.gz
~/Downloads/ft5955-v094-source.tar.gz
~/Projects/Fingerprint-FT5955/focaltech-5955-moh-test/packages/ft5955-native-validation-v0.9.1.tar.gz
```

The `7_Fingerprint-module.zip` vendor package is *not* presumed redistributable and may contain proprietary binaries. No archive is to be automatically extracted, executed, committed or uploaded; no fingerprint data or templates should enter the public source repository.

**Next evidence step:** compute local SHA-256 and archive member-name manifests, without extraction, for the FT5955 tarballs and compare duplicate names/hashes. Then reconcile source members with GitHub branches and the downloaded-file session chronology, before reviewing the dirty worktrees or working driver deployment.

## SHA-256 and package-to-GitHub inventory cross-check (28 October 2026)

The owner examined archives *without extraction or execution* using Python `hashlib.sha256` and `tarfile`. The result is **15 files in Downloads plus one copy inside the MOH checkout**, but only **14 distinct file hashes**: two pairs are byte-for-byte identical.

- `~/Downloads/ft5955-v094-source.tar.gz` and `~/Downloads/ft5955-v094-source (1).tar.gz` both SHA-256 `3762811926d28afd035241c649c27222d8ab7745f1591c4b8a84878243049a8d`.
- `~/Downloads/ft5955-native-validation-v0.9.1.tar.gz` and `~/Projects/Fingerprint-FT5955/focaltech-5955-moh-test/packages/ft5955-native-validation-v0.9.1.tar.gz` both SHA-256 `857d445ee7dc01e11a1aa7cec3bb9cdeb4685e859e0f2784631110877fb1979f`.

The download contains **13 distinct FT5955 source-package tarballs** plus a vendor `7_Fingerprint-module.zip` (not inspected here). Exact tarball hashes, file counts and existing version-directory counts:

| Local tarball | SHA-256 | Regular files in tar | Files in remote `research/source-history/` | Remote folder |
| --- | --- | ---: | ---: | --- |
| `ft5955-driver-sources.tar.gz` | `cb56078de9d0dcbe67a4cfbc529fdaa98810d0f8410c8344464f8e6b34ea7d2f` | 2 | 2 | `driver-sources-snapshot` |
| `ft5955-moh-ipc-v0.1.tar.gz` | `0a9d00af12acd8899b84e1ce94af80e619f413a802cc01003c8ed8a038334a01` | 2 | 2 | `v0.1-moh-ipc` |
| `ft5955-moh-ipc-v0.2.tar.gz` | `4b8e91a4627a08631868520e915213d59836969472b755a8598cb5034b877db5` | 4 | 4 | `v0.2-moh-ipc` |
| `ft5955-moh-ipc-v0.3.tar.gz` | `50a0c23feda590abfce4e3457414b0121e36dec47f07b5147362fee8eab20c03` | 12 | 12 | `v0.3-moh-ipc` |
| `ft5955-moh-template-v0.4.tar.gz` | `6d284f8a762779b8bab11aa1b8f6548c51797005edd7c4d9bd57cc3063a8c892` | 9 | 9 | `v0.4-moh-template` |
| `ft5955-moh-print-v0.5.tar.gz` | `2a42fe076138ae923a7bf1ba29df7e3588ed72c9cffbeb76aaddf6224e39eb1f` | 10 | 10 | `v0.5-moh-print` |
| `ft5955-moh-libfprint-v0.6.tar.gz` | `1c88fcf6f34ef13c795f00bf4525a09aae2556e832e449564cbcb8c4e4886ca1` | 10 | 10 | `v0.6-moh-libfprint` |
| `ft5955-moh-libfprint-v0.6.1.tar.gz` | `53dd2b3d81da20c766993422c8829e2e673942c69f1722b434526357951c3726` | **12** | **10** | `v0.6.1-moh-libfprint` |
| `ft5955-driver-actions-v0.7.tar.gz` | `039100b697dd6e059211cd522254a6edb45f176aa5425d9b47031edada31edad` | 17 | 17 | `v0.7-driver-actions` |
| `ft5955-driver-integration-v0.8.tar.gz` | `d3030d7ba0d26a3f167ffbfbdf4067eaf199905f7ee75de31a4e0674d6f55231` | 30 | 30 | `v0.8-driver-integration` |
| `ft5955-native-validation-v0.9.tar.gz` | `b734dc99f60b1cbae18956d5138a392fe674fada5eab944fedc48374aa209e63` | 5 | 5 | `v0.9-native-validation` |
| `ft5955-native-validation-v0.9.1.tar.gz` | `857d445ee7dc01e11a1aa7cec3bb9cdeb4685e859e0f2784631110877fb1979f` | 5 | 5 | `v0.9.1-native-validation` |
| `ft5955-v094-source.tar.gz` | `3762811926d28afd035241c649c27222d8ab7745f1591c4b8a84878243049a8d` | 6 | 6 | `v0.9.4-safety-tests` |

**Corrected finding:** Main GitHub already preserves these version directories as source files under `research/source-history/`, despite the original downloadable-package period. All 13 have corresponding directories and **12 have matching member counts**. **v0.6.1 has two more regular files in the archive than in its GitHub directory**; the exact membership difference and source relevance remain unknown until names and hashes are compared. Both match and mismatch figures are counts, **not byte-identical content verification**. A file-by-file Git blob SHA-1 comparison is the next required check; package naming alone is not authoritative. This evidence supersedes any suggestion that the full early package chain is absent from GitHub.

## Tested milestones versus deployment — distinguish carefully

- Historical timing trace: contact → image approximately **31 ms**, image → matcher reply **7.5 ms**, and a measured **~1,040 ms** cleanup wait. Subsequent removal of the `up.join(timeout=1)` relay join has source and synthetic regression evidence; a later live verified fix is documented elsewhere in this repository. The 20 October timing export stops at an *earlier* stage, so its `not yet hardware tested` wording must not override subsequent dated evidence.
- The 20 October identification export describes separate v1/v2 `identify` experiments. The owner observed that v2 did not reliably identify the left index (three no-matches and one match) and supplied a guarded **rollback to the original single-finger library** with a matching SHA-256. This establishes the state **at that historical checkpoint only**; do not infer the installed library's current contents or the effective PAM/UID955 MOH service from it.
- Existing `PROJECT_STATUS.md`, source-history branch records and KDE authentication notes must be reconciled with dated evidence and actual, read-only installed-file hashes before changing anything in the live stack.

## Recovery sequence — no destructive operations

1. **Inventory** the local source/download directories, relevant `*.tar.gz` packages, all dirty worktree diffs, untracked source files and source SHA-256 hashes. Treat any raw biometric captures as private, excluded.
2. **Map** each package/version → actual source tree → GitHub commit/branch or known missing source → observed build/test results → any installed artefact and rollback record. Label source, offline-test, hardware-tested, failed and superseded states separately.
3. **Reconcile** against current GitHub source at exact paths and content hashes; inspect unique local changes before deciding what belongs in maintained driver, tests or historical archive. Never overwrite local dirty files or expose biometric/vendor binary content.
4. **Read-only deployment checks:** capture installed libfprint library hash and current `fprintd` service-unit/drop-in/relay paths; compare against known-good records. Do **not** restart services, reenrol fingers or modify PAM to conduct this audit.
5. **Only when complete:** commit reviewed, non-sensitive missing source and maintenance docs to the existing source repository with deterministic tests, and update `README.md`, `PROJECT_STATUS.md`, this audit and branch inventory together.
6. **Only after source integrity and local worktree use are resolved:** seek explicit owner approval for a named remote-branch deletion list. A remote branch with zero unique commits is **not** proof its corresponding local worktree is clean or disposable.

## Current branch-pruning hold

The remote `feature/ft5955-driver-consolidation-20261017` and `feature/ft5955-source-history` branch tips are ancestors of `main`. However, the **source-history branch is checked out in a dirty local worktree**, so do not delete it remotely as a quick housekeeping measure. Preserve the divergent MOH, KDE, timing and relay branches, their open pull requests, build provenance and local worktrees until the recovery audit is closed.

**No branch deletions, source changes, live-driver modifications or shell commands have been performed as part of this checkpoint.**
