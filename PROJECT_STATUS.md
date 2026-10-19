# PROJECT STATUS — FocalTech USB 2808:5955 Linux driver

**Updated:** 19 October 2026  
**Repository entry point:** `main`. Latest dedicated-service work remains on existing `feature/kde-lock-auth-preflight-20261018`; no new branch created.  
**Purpose:** The first document to consult before proposing or implementing ANY change. This is a checkpoint, not a request to reopen resolved problems.

## Original objective (do not expand)

Get the **FocalTech 2808:5955 USB fingerprint reader** working on Linux through **libfprint → fprintd → existing PAM/KDE fingerprint authentication**, including screen unlock/authorisation. The immediate matching solution may use the already functioning proprietary Windows MOH matcher. **Long-term**: replace matching with a native Linux implementation.

This is a fingerprint **hardware/libfprint driver** project, **not** a project to rewrite KDE, PAM, fprintd, operating-system authentication or Linux user accounts. Prefer existing system capabilities.

## VERIFIED / COMPLETED — do not retest without evidence of regression

- Device identity, USB handshake, contact/release, raw image capture and conversion were established with physical hardware.
- A libfprint driver and real system fprintd have enumerated and operated the reader.
- Both **left and right index fingers** were successfully enrolled via KDE.
- Real MOH fingerprint matching works; standard `fprintd-verify` returned `verify-match`.
- **One-second timing error was identified and removed** during development. **User-reported result after the fix: 5 matches out of 5.** This reliability issue was considered **resolved**. Do not invent another timing or retry fix. **Known-good source:** `tools/ft5955_engine_broker.py` in `feature/ft5955-relay-latency`, commit `66e054c` (fixed by removing `up.join(timeout=1)` after gateway EOF). On 19 October this exact corrected broker was restored into both `main` and `feature/kde-lock-auth-preflight-20261018`, with the previously successful synthetic regression test. **On 19 October the installed copy was verified old (`68035014f464d6b5de8941adc00e6afd15c5719c`) and the user installed the exact verified fixed file (`6fa2dcf7ece70cabab19b9e2825f2255fa437a3f`); guarded installation printed PASS and saved `/opt/ft5955-dev/ft5955_engine_broker.py.before-1s-fix`. The corrected installed hash was checked by the install script, but no subsequent real fingerprint operation has yet been reported.**, which is a source/deployment-record question, not grounds to repeat the experiments.
- On **18 October 2026**, the separate UID955 MOH service completed real hardware verification: `fprintd-verify -f left-index-finger` returned `verify-match` on the first attempt.
- On **18 October 2026**, user confirmed **KDE screen unlocking actually succeeded with fingerprints**, including both fingers. Normal password unlock also still worked. The fingerprint option sometimes disappeared and required password fallback; **cause not established**. Do not presume a PAM retry limit or missing hardware reliability fix without checking installed code and live configuration.
- Historical standalone experiment was rolled back successfully on 17 October without replacing RPM-owned vendor libraries. A later experimental dedicated-service trial was activated; **no confirmed rollback of that later trial has been reported**.

## Important distinctions / unresolved source-of-truth gaps

- GitHub is authoritative for **committed** source and documented outcomes, but may **not** exactly match the currently running `libfprint` library, protected `/opt` service or locally modified checkout.
- The immutable driver source snapshot in `driver/live-snapshot-2026-10-16/` records earlier capture/verify logic. **Do not assume that historical snapshot contains the later one-second-delay fix or is identical to the running binary.**
- The exact 1-second cleanup fix is **identified**: `tools/ft5955_engine_broker.py` commit `66e054c`, originally trialled with staged timingtrace libfprint. The 18 October 5/5 round result and subsequent right-index five-round test are documented in `feature/ft5955-relay-latency/docs/relay-latency-hardware-pass-2026-10-18.md`. On 19 October the installed relay's OLD hash was directly checked and the proven fixed source was installed with a verified Git blob hash and backup. No post-deployment authentication result is yet reported; leave PAM/config unchanged.
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

## 19 OCTOBER 2026 — restored backend and re-enrolment result

- During earlier `fprintd-verify` attempts, the USB/handshake/contact/capture stages passed, but verification ended in `verify-unknown-error`. Journals reported `Error writing to file descriptor: Broken pipe`, with no `gateway_ready` marker. Both `ft5955-engine-dev.socket` and the service showed `inactive`; service `Result=success` did **not** indicate a running listener.
- The protected development protocol and fprintd gateway routing were still marked active. User explicitly ran `sudo systemctl start ft5955-engine-dev.socket` and confirmed the socket was `active`. This manually started it; no evidence yet that it is enabled persistently after reboot.
- Subsequent normal `fprintd-verify -f left-index-finger` attempts reached real `verify-no-match` and `verify-match` decisions, confirming that the earlier broken-pipe failure no longer blocked the matching path.
- User reported unsatisfactory matching and then **re-enrolled the left-index finger**. Submitted chronological terminal output contains **18** normal verifications: first 11 show **2 MATCH / 9 NO_MATCH**; final 7 show **7 consecutive MATCH / 0 NO_MATCH**, consistent with the user's before/after account. The re-enrolment operation itself is not included in the pasted terminal logs, so the grouping boundary is inferred from their explanation.
- Seven final command timings: **1.713 s, 0.554 s, 0.487 s, 0.395 s, 0.518 s, 0.594 s, 0.433 s** (median **0.518 s**). These are shell elapsed times, **not** isolated matcher or sensor latencies. This small uncontrolled run suggests re-enrolment materially improved matching for this finger; it does not establish overall accuracy or a production authentication safety guarantee.
- **Do not repeat the completed matching/timing baselines**, re-enrol again, change USB polling, rebuild the libfprint stack, or modify KDE/PAM to explain this now-working experiment. The protected Windows-MOH service still has previously documented security limitations for production use; preserve password fallback and the saved relay backup.

## NEW 19 OCTOBER 2026 post-installation observation

- User's installation script reported `PASS: Proven one-second relay fix installed. Original safely backed up.` Root-owned installed broker replaced previously measured old `68035014...` blob with hash-checked `6fa2dcf7...` code; no service restart or PAM/libfprint configuration edits.
- The **first subsequent** `fprintd-verify -f left-index-finger` enumerated the enrolled left/right fingers, entered `Verifying: left-index-finger`, and returned **`verify-unknown-error (done)`**.
- Unknown error differs from a biological `verify-no-match`; there is no evidence yet that the restored fix caused it or that matching accuracy changed. Consult existing journal messages **before** proposing changes or a repeat scan.
- Historical 18 October 5/5 results remain valid evidence of the previously tested code. Do not delete the `.before-1s-fix` backup.

## REMAINING — only the actual project work

1. **Confirmed on the live host:** corrected relay installed with backup, development MOH socket restored to active, end-to-end verification regained, and the final seven left-index checks after user re-enrolment all returned MATCH. No more verification baseline work for this milestone. Check only the socket's reboot activation policy before consolidating the maintainable install/rollback instructions.
2. Consolidate the existing working libfprint driver, build/installation/rollback and documentation into a maintainable project state, using existing Linux services.
3. Record realistic operating/security limitations without endlessly introducing new subsystems. Keep normal password authentication available.
4. Later, as a separate explicitly authorised phase, build a **native Linux fingerprint matcher** to remove the proprietary Windows MOH dependency.

## NEXT ACTION

**Verified operating state (19 October):** the protected MOH socket was found inactive despite the development trial being marked active; manually starting `ft5955-engine-dev.socket` restored end-to-end verification. After re-enrolment the last **7/7** reported left-index attempts matched (median command time **518 ms**). No more fingerprint scans or speed tuning are needed for this milestone. **Next:** read-only inspection of whether the existing socket unit will start after reboot, then consolidate and document the already-working reversible libfprint/fprintd integration and review pre-existing MOH/template trust limitations *before* treating KDE/PAM authentication as production-ready. Preserve the original relay backup and password unlock.

At the start of each new chat, read this file and report **COMPLETED / REMAINING / NEXT ACTION**. Never silently convert a hypothesis into a fault or repeat earlier testing. Update this file when a significant result changes the project state.

## Historical evidence

- `docs/next-session-handoff.md` — original lab and timing experiments; contains **dated historical snapshots**, not necessarily current state.
- `docs/kde-short-lived-trial-2026-10-17.md` — both fingers enrolled, matching and initial rollback.
- `docs/ft5955-dev-real-service-handoff-2026-10-18.md` — actual dedicated-service verification match.
- `docs/roadmap.md` — milestones and archive; read dated statements in chronological context.

**Conflicts in historical documents must be reconciled by newer user-observed facts and real code/deployment evidence, not by adding another experiment.**
