# FocalTech 5955 — source and deployment reconciliation checkpoint

**Audit date:** 28 October 2026. **Status:** INCOMPLETE — **do not delete FocalTech research branches, reset dirty worktrees, reinstall libfprint or change PAM/systemd during this inventory.** This note records a source recovery risk, not a new driver implementation or approval for production biometric authentication.

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
