# PROJECT STATUS — FocalTech USB 2808:5955 Linux driver

**Updated:** 18 October 2026  
**Source branch:** `feature/kde-lock-auth-preflight-20261018` (existing; no new branch)  
**Purpose:** The first document to consult before proposing or implementing ANY change. This is a checkpoint, not a request to reopen resolved problems.

## Original objective (do not expand)

Get the **FocalTech 2808:5955 USB fingerprint reader** working on Linux through **libfprint → fprintd → existing PAM/KDE fingerprint authentication**, including screen unlock/authorisation. The immediate matching solution may use the already functioning proprietary Windows MOH matcher. **Long-term**: replace matching with a native Linux implementation.

This is a fingerprint **hardware/libfprint driver** project, **not** a project to rewrite KDE, PAM, fprintd, operating-system authentication or Linux user accounts. Prefer existing system capabilities.

## VERIFIED / COMPLETED — do not retest without evidence of regression

- Device identity, USB handshake, contact/release, raw image capture and conversion were established with physical hardware.
- A libfprint driver and real system fprintd have enumerated and operated the reader.
- Both **left and right index fingers** were successfully enrolled via KDE.
- Real MOH fingerprint matching works; standard `fprintd-verify` returned `verify-match`.
- **One-second timing error was identified and removed** during development. **User-reported result after the fix: 5 matches out of 5.** This reliability issue was considered **resolved**. Do not invent another timing or retry fix. **The commit/binary containing that exact fix has NOT yet been mapped to the installed build**, which is a source/deployment-record question, not grounds to repeat the experiments.
- On **18 October 2026**, the separate UID955 MOH service completed real hardware verification: `fprintd-verify -f left-index-finger` returned `verify-match` on the first attempt.
- On **18 October 2026**, user confirmed **KDE screen unlocking actually succeeded with fingerprints**, including both fingers. Normal password unlock also still worked. The fingerprint option sometimes disappeared and required password fallback; **cause not established**. Do not presume a PAM retry limit or missing hardware reliability fix without checking installed code and live configuration.
- Historical standalone experiment was rolled back successfully on 17 October without replacing RPM-owned vendor libraries. A later experimental dedicated-service trial was activated; **no confirmed rollback of that later trial has been reported**.

## Important distinctions / unresolved source-of-truth gaps

- GitHub is authoritative for **committed** source and documented outcomes, but may **not** exactly match the currently running `libfprint` library, protected `/opt` service or locally modified checkout.
- The immutable driver source snapshot in `driver/live-snapshot-2026-10-16/` records earlier capture/verify logic. **Do not assume that historical snapshot contains the later one-second-delay fix or is identical to the running binary.**
- The actual 5/5 success result is explicitly user reported; the **precise local file/commit/library SHA responsible is still to be identified from existing development history**, preferably without repeating hardware tests.
- User's inspection on 18 October found `/etc/pam.d/kde-fingerprint` identical to the saved original and `fingerprint-auth` containing `pam_debug.so auth=authinfo_unavail`, *even though* KDE fingerprint unlock had succeeded. **Do not infer effective PAM flow from an assumed rule.** Earlier attempts to modify `max-tries` stopped due to mismatched config, making no changes.
- Experimental MOH trust/template integrity and sandbox decisions have **not** been approved as production authentication security. That remains separate from validating the operational driver. Never sacrifice password fallback.

## Scope guard — repeatedly rejected detours

- NO more arbitrary timeout/polling/delay alterations without evidence that the proven 1-second fix is absent or regressed.
- NO new internal matcher `NO_MATCH` retry mechanism; fprintd/PAM/KDE already own authentication flow. An unnecessary four-touch build-script transformation was **reverted**, commit `b7c3efa`.
- NO re-enrolment or replay of completed USB/sensor baselines.
- NO rewriting PAM, SDDM, sudo or authselect; use documented standard Linux integration. Do not alter authentication as a side-effect of a driver experiment.
- NO additional branches, directories, standalone services, or parallel architectures without express user approval.
- Protect dirty worktrees, staged shared libraries, previous verified builds, and old research branches. No reset/clean/deletion without explicit agreement.

## Existing repository / development branches

At this checkpoint, GitHub reports **9 branches including `main`**. The `feature/kde-lock-auth-preflight-20261018` branch contains recent MOH service and KDE work. Consolidation into `main` should be planned **after** reconciling the known-good local driver and running code; do not add more branches or delete history reflexively. The branch/commit count alone is not a progress metric.

## REMAINING — only the actual project work

1. **Reconcile existing source with verified results**: locate the already-corrected one-second timing implementation and confirm which code/binary is installed. This is about identifying and consolidating **what already works**, not tuning it again. Preserve all local changes.
2. Consolidate the existing working libfprint driver, build/installation/rollback and documentation into a maintainable project state, using existing Linux services.
3. Record realistic operating/security limitations without endlessly introducing new subsystems. Keep normal password authentication available.
4. Later, as a separate explicitly authorised phase, build a **native Linux fingerprint matcher** to remove the proprietary Windows MOH dependency.

## NEXT ACTION

**Do not implement or test any new proposed fix yet.** First use the existing GitHub history and relevant prior conversations to identify the exact **5/5-working implementation** and compare it with the current deployed driver. Report the difference (if any) before requesting a change.

At the start of each new chat, read this file and report **COMPLETED / REMAINING / NEXT ACTION**. Never silently convert a hypothesis into a fault or repeat earlier testing. Update this file when a significant result changes the project state.

## Historical evidence

- `docs/next-session-handoff.md` — original lab and timing experiments; contains **dated historical snapshots**, not necessarily current state.
- `docs/kde-short-lived-trial-2026-10-17.md` — both fingers enrolled, matching and initial rollback.
- `docs/ft5955-dev-real-service-handoff-2026-10-18.md` — actual dedicated-service verification match.
- `docs/roadmap.md` — milestones and archive; read dated statements in chronological context.

**Conflicts in historical documents must be reconciled by newer user-observed facts and real code/deployment evidence, not by adding another experiment.**
