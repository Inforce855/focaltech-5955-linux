# Git branch register — FocalTech 2808:5955 Linux driver

**Reviewed:** 18 October 2026 against GitHub `main`. **Source/documentation follow-up:** 19 October 2026 — the already-verified ~1-second relay fix and regression test were copied without modification to both `main` and `feature/kde-lock-auth-preflight-20261018`; the README now links to the actual KDE milestone. The GitHub source correction has **not** been deployed to the user's host. This document is the **authoritative branch map**, not an instruction to install experimental code. First read [PROJECT_STATUS.md](../PROJECT_STATUS.md).

## Protecting `main` — owner action required (28 October 2026)

**Updated protection status (28 October 2026):** the owner created a classic branch protection rule and GitHub's branch API now reports **`main.protected=true`**. This is confirmed active protection, not merely a recommendation. The owner reports leaving all checkboxes unticked. Under classic protection, force pushes and deletion are blocked by default, but admin bypass remains possible unless **Do not allow bypassing the above settings** is checked. The owner can enable that one control to ensure the restriction applies to their own admin account. No mandatory pull requests or CI gates are currently configured. The original recommendations remain:

- Leave **Allow force pushes** and **Allow deletions** off. Enable **Do not allow bypassing the above settings** if the owner wants protection to apply to their administrator account as well.
- Do **not** enable mandatory approving reviews or make the branch read-only merely to clear the warning. Both could obstruct legitimate maintenance.
- Current `.github/workflows/ft5955-synthetic-broker.yml` has a `synthetic-broker` CI job with previously successful runs on `main`, but its events are **push** on `main` and a named feature branch, plus manual dispatch; there is **no `pull_request` trigger**. Do not make it a required PR status check until a working PR trigger and merge checks are tested.
- After protecting the branch, retain feature branches with unique MOH/KDE/PAM hardware evidence until their exact commits, deployed source and rollback are verified. Historical branch comparison notes identify `feature/ft5955-driver-consolidation-20261017` and `feature/ft5955-source-history` as already ancestral to `main` (18 October audit); re-check local worktree references before approving their deletion. Never mass-delete research branches.
- GitHub's current documentation: [Managing branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule).

This note documents recommended configuration only. It **does not** turn on protection or modify the authentication driver, PAM, packages or host state.

## Reverified branch ancestry — 28 October 2026

GitHub comparison against today's `main` shows exactly two branches with **zero unique commits**:

- `feature/ft5955-driver-consolidation-20261017` — 0 ahead / 63 behind `main`.
- `feature/ft5955-source-history` — 0 ahead / 173 behind `main`.

Both are *candidates for owner-approved deletion after checking local worktrees and installer references*; their commits are already reachable from `main`. They are not current open pull-request heads. No branches were deleted.

The other six named feature branches retain unique commits relative to main: `early-contact-parallel` (14), `moh-engine-bridge` (419), `private-fprintd-v096` (15), `relay-latency` (70), `timingtrace` (22), and `kde-lock-auth-preflight-20261018` (104). Four open PRs (#1, #5, #6, #7) are based on the MOH/timing/relay development chain. This is valuable hardware and PAM research history; no blanket deletion or forced merge should be attempted.

## Original goal

Make the **FocalTech USB fingerprint reader work through the existing Linux `libfprint` → `fprintd` → KDE/PAM framework**. Use the working MOH matcher as an interim dependency; a fully native Linux matcher is a future phase. **Do not rewrite Linux authentication or create duplicate login/retry frameworks.**

## Rules

- **`main` is the project entry point**: document all retained/temporary branches here, and keep README/status and real test results current.
- Experimental feature branches are temporary development lanes. Merge confirmed improvements to `main` with accompanying documentation, or explicitly label retained research; retire branches only after checking for unmerged work and obtaining user approval.
- The existence of a branch or positive synthetic test does **not** establish that its code is installed, secure for PAM, or ready to merge.
- Don't create new branches, alternate services, worktrees or installers without a specific user-approved need. Do not rewrite/delete dirty local worktrees or pinned historical snapshots.

## Branches (9 total including `main`)

GitHub branch comparisons were performed on **18 October 2026**; counts are relative to `main`, and will change with future commits.

| Branch | Comparison with main | Purpose / demonstrated status | Handling |
| --- | --- | --- | --- |
| [`main`](https://github.com/Inforce855/focaltech-5955-linux/tree/main) | Baseline | Earlier USB/libfprint driver, system trial and 17 October KDE enrol/verification work | Authoritative integration branch; its 17 October README is **historical**, not a complete record of 18 October |
| [`feature/ft5955-driver-consolidation-20261017`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-driver-consolidation-20261017) | 0 ahead, 17 behind | Earlier consolidated driver implementation | All commits already ancestors of `main`; review local use before retiring |
| [`feature/ft5955-source-history`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-source-history) | 0 ahead, 127 behind | Historical source/provenance work | Already ancestral to `main`; reference-only pending approved cleanup |
| [`feature/ft5955-private-fprintd-v096`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-private-fprintd-v096) | 15 ahead, 146 behind | Earlier private-fprintd experiments | Diverged historical research; don't treat it as latest production driver |
| [`feature/ft5955-moh-engine-bridge`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-moh-engine-bridge) | 419 ahead, 213 behind | Large proprietary-MOH-engine bridge research history, code and tests | Diverged and **substantial unmerged work**; review before retirement/merge |
| [`feature/ft5955-early-contact-parallel`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-early-contact-parallel) | 14 ahead | Experimental capture/arming variants | Retain as test evidence until reconciled with the working driver |
| [`feature/ft5955-timingtrace`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-timingtrace) | 22 ahead | Monotonic capture/matcher/cleanup event tracing | Historical timing experiment; see subsequent latency branch |
| [`feature/ft5955-relay-latency`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-relay-latency) | 36 ahead | **Real tested removal of the approximately 1-second relay-cleanup delay**, reducing cleanup to about 40 ms; documented five-round verification success | **Important verified work not to lose.** See [hardware results](https://github.com/Inforce855/focaltech-5955-linux/blob/feature/ft5955-relay-latency/docs/relay-latency-hardware-pass-2026-10-18.md) |
| [`feature/kde-lock-auth-preflight-20261018`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/kde-lock-auth-preflight-20261018) | 61 ahead | Independent UID955 real MOH service, fprintd verification, actual KDE fingerprint unlocking, project checkpoint | Most recent KDE integration work; no confirmed main integration/production security approval |

**Important nuance:** the 1-second delay above was measured during the Python relay/engine **cleanup**, not proven to be a one-second wait *before image capture*. The referenced hardware report measured cleanup dropping from ~1,040 ms to ~40 ms, with additional 5/5 rounds matched. The user's verified success must not be discarded, but it must not be misdescribed as formal 100% per-scan matching accuracy.

## Why `main` currently looks stale

The root README on `main` was **out of date until 19 October**; it originally described only the 17 October milestone. It now includes a dated status note recording real KDE unlock and the existing latency fix. On **18 October**, the user explicitly reported that **KDE actually unlocked with fingerprints**, that both index fingers were enrolled, that the protected MOH service returned a genuine `verify-match`, and that password unlocking remained possible. The latest 18 October record exists on the KDE feature branch, and the 1-second delay fix and 5/5 observations exist on the latency feature branch. The facts and the proven relay fix are now recorded on `main`, but the **separate dedicated-service development implementation has not been merged into `main`**. The installed host's `/opt/ft5955-dev/ft5955_engine_broker.py` version remains to be established.

**Do not resolve this by blindly merging every development branch**: source/runtime correspondence, local uncommitted work, service trust and pinned artefacts must be checked first. It is safe and necessary to document real milestones now.

## Required branch discipline

1. Check current source, local install and feature status before a change.
2. Record a feature branch's purpose, entry condition, tested outcome, merge/supersession and clean-up approval *in this file*.
3. After user-verified success, integrate the **actual working changes**, with tests and docs, not an alternative implementation of the same already-resolved problem.
4. Keep `README.md`, `PROJECT_STATUS.md`, this register and the roadmap consistent.
5. Do not delete a research branch simply to reduce the count; identify unique commits and active local worktrees first.
