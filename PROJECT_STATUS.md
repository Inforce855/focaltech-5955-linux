# PROJECT STATUS — FocalTech USB 2808:5955 Linux driver

**Updated:** 19 October 2026  
**Repository entry point:** `main`. Latest dedicated-service work remains on existing `feature/kde-lock-auth-preflight-20261018`; no new branch created.  
**Purpose:** The first document to consult before proposing or implementing ANY change. This is a checkpoint, not a request to reopen resolved problems.

## Original objective (do not expand)

Get the **FocalTech 2808:5955 USB fingerprint reader** working on Linux through **libfprint → fprintd → existing PAM/KDE fingerprint authentication**, including screen unlock/authorisation. The immediate matching solution may use the already functioning proprietary Windows MOH matcher. **Long-term**: replace matching with a native Linux implementation.

This is a fingerprint **hardware/libfprint driver** project, **not** a project to rewrite KDE, PAM, fprintd, operating-system authentication or Linux user accounts. Prefer existing system capabilities.

**Latest outcome (19 October):** User confirms fingerprint setup survived reboot after enabling the MOH socket. Hardware verification and timing fix were previously demonstrated; next work is consolidation, not new matching experiments.

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

## 19 OCTOBER 2026 — post-reboot confirmation (user-reported)

- After enabling `ft5955-engine-dev.socket` with `sudo systemctl enable`, the user **confirmed that the working fingerprint setup survived a full reboot**. This closes the previously pending restart-persistence milestone on the basis of the user's report; no new command output or quantitative post-reboot test log was supplied in this message.
- Previously established on the live host: normal `fprintd-verify` reached the protected MOH matching backend, the exact known-good one-second relay teardown fix was installed with its original backed up, and the final seven post-re-enrolment left-index verifications all matched.
- No further baseline fingerprint scans or timing changes are required for this milestone. Existing protected MOH/template security restrictions still prevent claiming a production-ready authentication solution.

## 19 OCTOBER 2026 — MOH socket boot enablement configured (reboot test pending)

- User ran `sudo systemctl enable ft5955-engine-dev.socket`; systemd reported creation of `/etc/systemd/system/sockets.target.wants/ft5955-engine-dev.socket` pointing to the existing unit.
- A subsequent `systemctl is-enabled ft5955-engine-dev.socket` returned **`enabled`** (previously `disabled`). The socket was already manually started and its live status had returned `active` earlier in the session.
- **Not yet tested:** whether the socket starts automatically and ordinary `fprintd-verify -f left-index-finger` matches after a full reboot. Do not claim boot-time success yet.
- After reboot, read only `systemctl is-enabled ft5955-engine-dev.socket` and `systemctl is-active ft5955-engine-dev.socket`, followed by one normal user-level fingerprint verification if the socket is active. Preserve password fallback; no PAM or driver edits.

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

## 19 OCTOBER 2026 — global authselect fingerprint enabled (live host)

User explicitly ran the previously prepared guarded activation:

```sh
backup="ft5955-pre-fingerprint-$(date +%Y%m%d-%H%M%S)"
sudo authselect enable-feature with-fingerprint --backup="$backup"
authselect check
authselect current
grep -n 'pam_fprintd.so' /etc/pam.d/fingerprint-auth /etc/pam.d/system-auth
```

**Actual results:**
- Backup created: `/var/lib/authselect/backups/ft5955-pre-fingerprint-20261019-113538`.
- `authselect check`: **Current configuration is valid.**
- Profile `local`; features `with-silent-lastlog`, `with-mdns4` **and `with-fingerprint`**.
- `/etc/pam.d/fingerprint-auth:7`: `auth [success=done default=bad] pam_fprintd.so`.
- `/etc/pam.d/system-auth:8`: `auth sufficient pam_fprintd.so`.
- Existing working FocalTech driver and separate protected service were not changed as part of this authselect operation. **Do not describe activation as a successful KDE lock-screen, Polkit or sudo fingerprint test yet.** These are distinct pending checks.
- **Rollback option:** `sudo authselect backup-restore ft5955-pre-fingerprint-20261019-113538` (this restores the previous authselect-generated files and selection). Keep password recovery available before any lock-screen experiment.
- Security caveat: the protected UID955 MOH bridge is still experimental; global PAM now trusts it for potentially privileged authentication. This operational trial is not an independent audit of template authenticity, user binding or the proprietary engine's sandbox.

**Next:** begin with a harmless, explicit Polkit test while the session remains unlocked; verify presence of password fallback, then evaluate KDE's `Authenticators/Fingerprint` configuration before risking screen locking. Preserve rollback name, all working binaries and `-dev` service until the maintained migration passes.

## 19 OCTOBER 2026 — verified root-owned fprintd path (user-supplied diagnostic)

- `systemctl show fprintd.service -p User -p Group -p Environment -p DropInPaths`: `User=` and `Group=` unset (system default root service); `Environment=LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib FT5955_EXPERIMENTAL_ENABLE=1 FT5955_ENGINE_GATEWAY=/opt/ft5955-dev/ft5955_dev_relay.py`. The output of `DropInPaths=` was **truncated** by the terminal, but showed at least distribution `10-timeout-abort.conf`, the existing trial `90-ft5955-system-trial.conf` and another `95-f...` override.
- `namei -l /opt/ft5955-dev/ft5955_dev_relay.py`: parent directories root-owned, file `root:root 0644`, not writable by ordinary users.
- `find /opt/ft5955-system-trial/lib -maxdepth 1`: directory `root:root 0755`; library `libfprint-2.so.2.0.0` `root:root 0644`; `libfprint-2.so.2` symlink `root:root`. The actual symlink destination was not printed; do not claim it was independently resolved.
- Combined with the prior root-protected MOH service, `SO_PEERCRED` peer restriction and protected template directories, no unprivileged *writeable component* has been identified in the displayed privileged load path. This does **not** prove end-to-end security: keep the recorded concerns about identity/template authenticity, vendor DLL and read-only `/proc` sandbox boundary.
- User's requested target is **global `authselect with-fingerprint`**, not KDE-only. Fedora authselect supports `enable-feature with-fingerprint --backup=NAME` and `backup-restore NAME` for controlled activation/rollback. At this checkpoint, **the feature has not yet been reported enabled**. Preserve password access, the existing `local` profile features, and the installed working service. No more reader baseline tests.

## 19 OCTOBER 2026 — follow-up authselect and KDE configuration (user supplied)

Read-only host output:
- `authselect current`: profile `local`; features `with-silent-lastlog`, `with-mdns4` (no `with-fingerprint`). `authselect check`: `Current configuration is valid.`
- `/etc/pam.d/kde`: `auth substack password-auth`; `auth include postlogin`. Password-based lock screen remains configured.
- `/etc/pam.d/system-auth`: `pam_env.so`, `pam_faildelay.so delay=2000000`, `pam_unix.so nullok` (sufficient), `pam_deny.so`. No `pam_fprintd.so` in displayed rules.
- `/etc/pam.d/fingerprint-auth`: `auth required pam_debug.so auth=authinfo_unavail`; the KDE-specific fingerprint route currently cannot use enrolled prints.
- `kreadconfig6 --file kscreenlockerrc --group Authenticators --key Fingerprint --default false`: `false`. This is a relevant opt-in setting, but source/runtime behaviour on the user's exact KDE build must be confirmed before treating it as definitive.
- Package `fprintd-pam` **is installed** (from preceding diagnostic), and Polkit `polkit-1` includes `system-auth`; no fingerprint module is in the shown `system-auth` configuration.

**Decision:** do NOT blindly enable authselect `with-fingerprint`: that would alter shared `system-auth` used by Polkit and other components. The protected MOH service still has an unauthenticated SHA256 template envelope and pending vendor sandbox/identity review. Narrow KDE-only fingerprint activation and Polkit authorisation remain explicit goals, **pending the trust boundary review and guarded rollback**. Do not replace `pam_debug` directly in generated authselect files; they are authselect-managed. No fingerprint hardware retests.

## 19 OCTOBER 2026 — current PAM diagnostic supplied by user

User read-only command output from current Nobara host:
- `rpm -q fprintd-pam` -> `fprintd-pam-1.94.5-5.fc44.x86_64` (**installed**; supersedes the dated 18 Oct statement that the package was absent).
- `/etc/pam.d/kde-fingerprint`: `auth substack fingerprint-auth`; `auth include postlogin`.
- `/etc/pam.d/fingerprint-auth`: `auth required pam_debug.so auth=authinfo_unavail` (**placeholder, not pam_fprintd.so**).
- `/usr/lib/pam.d/polkit-1`: `auth include system-auth`. No current `system-auth` content was supplied; **do not infer Polkit fingerprint support from this line alone**.
- Dedicated KDE fingerprint PAM rule currently cannot call fprintd through the shown `fingerprint-auth` stack. Historical experimental KDE unlocking is a separate observation and does not establish which PAM rules are currently active.
- **Next (read-only):** inspect `authselect current`, `authselect check`, actual `system-auth` and `kde` authentication includes, and any KScreenLocker fingerprint flag, without changing or enabling PAM. Preserve old complete PAM backup and password unlock. Production activation still gated on matcher/template trust boundary.

## Explicit user completion goal — KDE screen unlock and authorisation (19 October 2026)

The user explicitly confirmed that **finishing this driver includes enabling fingerprint authentication for the KDE screen locker/screensaver and authorisation dialogs**, not merely obtaining `fprintd-verify` matches. Target these existing OS components with password fallback:
1. **KScreenLocker / `kde-fingerprint` PAM** — reliable normal screen unlock. Historical 18 October unlocking succeeded experimentally; revalidate *configuration and security*, not sensor recognition. Prior PAM inventory showed `fingerprint-auth` had `pam_debug.so auth=authinfo_unavail` and `fprintd-pam` missing; do not assume those rules have since changed or that earlier unlock establishes a supported configuration.
2. **Polkit KDE authorisation dialogs** — inspect effective Polkit PAM service configuration and selectively integrate when matcher/template trust is adequate.
3. **`sudo`** — user said authorisation “etc.”; treat terminal sudo as an optional, separate last-stage integration, not implied permission to alter it immediately.
4. **Initial display-manager login** — separate from unlocking; do not change SDDM or the Plasma login manager without an explicit scoped plan. Preserve password and wallet behaviour.

**Safety gates before privileged PAM use:** the current UID955 MOH service is operational, but review saved-template integrity and user identity binding, control of matcher decisions, the vendor `FT5955_ALLOW_UNVERIFIED_ATTACH` option and sandbox isolation; fail closed on backend errors and wrong peers. Do not globally enable authselect `with-fingerprint` or install `fprintd-pam` blindly; the current guarded FT5955 lab launcher rejects such use. Use existing `docs/kde-screen-unlock-security-preflight-2026-10-18.md` and `tools/ft5955_kde_auth_preflight.sh` as the starting point for **read-only** OS state review. After gates are met, implement minimal per-service PAM adjustments and test password fallback with explicit rollback, without rewriting Linux authentication. No new driver baselines or extra branches.

## Release transition — retire the `-dev` designation (explicit user requirement)

The user wants a maintained, normal FocalTech 5955 Linux driver and **does not want the working installation permanently labelled or operated as `dev`**. This requirement must not be dropped when consolidating source into `main` or completing KDE/Polkit/PAM integration.

- Preserve the currently functioning `ft5955-engine-dev.service`, `ft5955-engine-dev.socket` and `/opt/ft5955-dev` until a replacement has passed installation, restart, matching, password-fallback and rollback checks.
- After closing the recorded MOH matcher trust/template security questions, create one documented, maintainable non-development service and installer/upgrade/rollback path from the existing verified code; only then retire the `-dev` service names, paths, development markers and obsolete scripts.
- Do not mistake a rename for security or completion; no premature rename, parallel runtime or destructive cleanup. Keep the fully native Linux matcher as a separately planned later milestone.

## 19 OCTOBER 2026 — exact service inventory and guarded identify swap source committed

User's `systemctl cat` confirms fprintd drop-ins `90-ft5955-system-trial.conf` (experimental libfprint loader, enabled) and `95-ft5955-moh-dev-gateway.conf` (effective protected UID955 relay `/opt/ft5955-dev/ft5955_dev_relay.py`). Original `FT5955_TRIAL_OWNER` marker **matches the known-good library SHA** `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`. Staged identify checksum `70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd` was independently verified. **No overrides, protected engine, PAM or saved prints need modification.**

Source-only `tools/ft5955_identify_live_trial.sh` created on existing `feature/ft5955-relay-latency`: guarded `--status`, `--activate`, `--rollback`. Backups original root binary+marker to `/opt/ft5955-system-trial/.identify-rollback-20261019` (0700), checks hashes and effective service environment, and swaps only experimental libfprint .so plus existing owner marker using atomic renames. Requires inactive fprintd; does not start/stop services, alter PAM, touch enrollments or bypass historical installer guard. Offline `tests/test_ft5955_identify_live_trial.py` and GitHub workflow `bash -n` step added. **These tests/swap have not yet been user-executed; no real fingerprint identify result yet.** Next fast-forward user's existing clean detached-HEAD checkout, run syntax/unit test then `--status` before discussing activation. Preserve password fallback and roll back if unexpected behaviour.

## 19 OCTOBER 2026 — identify live-vs-staged integrity preflight PASS

User confirmed `sha256sum -c SHA256` for `stage-identify`: **OK**, SHA-256 `70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd` (owner `tim:tim`, mode 0600). Installed known-good `/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0`: SHA-256 `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28` (owner `root:root`, mode 0644). `fprintd.service` inactive with `MainPID=0`, and both 90-/95- custom override paths in `DropInPaths` (95 path truncated). No files changed. **Next: read-only full override/marker inventory, then guarded backup-and-rollback for live identify swap.** Old lab install guard against active `fprintd-pam` must not be bypassed. No real identify test yet.

## 19 OCTOBER 2026 — identify staged build SUCCESS, original authentication untouched

The user ran `verify_ft5955_clean_clone.py --stage --trace-timing --identify` in existing `~/Projects/ft5955-relay-latency-test`. Verified pinned upstream and source patch manifest; Ninja **109/109 PASS**. New **user-only** `stage-identify` library created at `/home/tim/.local/state/ft5955-system-trial/stage-identify/lib/libfprint-2.so.2.0.0` with reported SHA-256 **`70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd`**. No file in `/opt`, `/etc` or `/usr` touched; no USB, active fprintd, global PAM, enrolled prints or MOH engine changed. **No hardware identify PASS yet.** Details: `docs/identify-source-2026-10-19.md` on existing `feature/ft5955-relay-latency`.

Next: read-only source/stage SHA-256 verification and inventory of actual installed binary and fprintd drop-ins; then implement guarded reversible replacement with exact known-good backup and independent password fallback. Do not reuse old trial install scripts: they deliberately refuse if `fprintd-pam` is installed. Keep all local dirty repos and old build stages unchanged.

## 19 OCTOBER 2026 — identify offline tests and clean compile PASS

User-provided full run: existing detached-HEAD checkout fast-forwarded `66e054c..ccfdd59` without overwriting local changes. `test_ft5955_identify_overlay.py` **4/4 PASS**. Isolated `verify_ft5955_clean_clone.py --build --trace-timing --identify` independently retrieved exact libfprint v1.94.100 commit `80a4b5ec`, verified and applied all three source patches, added 100ms polling + early-capture + timing trace + identify overlay to disposable source, and **compiled Ninja 109/109 PASS**. It explicitly removed the disposable source/build and left current live driver, fprintd, PAM and fingerprints untouched. **Not yet** staged or installed, no real multi-finger test yet. Next safely stage using `--stage --trace-timing --identify` in the existing checkout and plan a separate guarded installer; older short-lived KDE trial installer refuses active `fprintd-pam` and must not be bypassed.

## 19 OCTOBER 2026 — identify code committed source-only on existing latency branch

**User-supplied SHA-256 source check conclusively matched historical GitHub snapshot:** `focaltech_5955.c` `40418e509506400a4118a35f76a0482ad614b855d285d88971e342b81ebad703`, `ft5955_native_action.c` `0f52c8de56f4ee524f1225bd0db559262505c21f906b4034def1e01d61ec94ab`, `ft5955_native_action.h` `4c7098d939e792540d82320dd9bcf2eb5899dec9571cc8172d22b9541c5629ee`. The installed libfprint binary *does* contain `FT5955TIMING`, which was added during a disposable timingtrace build on `feature/ft5955-relay-latency`. The apparent source discrepancy is therefore explained by that transform; do not rebuild from untransformed local files.

**Code progress on already-existing `feature/ft5955-relay-latency` branch (no new branch):**
- Added `tools/ft5955_identify_overlay.py`: source-only, opt-in `identify` callback in a disposable reconstructed libfprint tree, keeping current enrol/verify and timing transformations intact. Matches one fresh captured frame against each enrolled `FpPrint` provided by libfprint through isolated protected MODE V sessions. Reports gallery match or real no-match; bounds captures/gallery and fails closed on invalid template, timeout, cancellation and protocol faults.
- Enhanced `tools/verify_ft5955_clean_clone.py` with `--trace-timing --identify --build` or `--stage`, the latter only a new **non-installable user-owned** `stage-identify` library. Neither changes live `/opt`, PAM or established staged variants.
- Added `tests/test_ft5955_identify_overlay.py` and corresponding existing offline GitHub Actions test step.
- Documented implementation, source provenance and gates in `docs/identify-source-2026-10-19.md` on the existing latency branch. All historical checksum-verified snapshot source remains unchanged.

**Do not overclaim:** source commits exist; compiled build, CI success and live hardware identify have **not yet been confirmed**. Next is safe fast-forward of existing latency checkout if clean, offline unittest, then clean upstream v1.94.100 build without USB/installation. **Never replace the working installed library based on source-only tests.** After compilation, separately plan guarded backup/rollback and real identify validation with both enrolled index fingers. Maintain protection of all dirty local worktrees and the previously corrected broker.

## 19 OCTOBER 2026 — identify implementation entry point (source check required)

User requested **implement multi-finger identification now**. Both index fingers are already enrolled; no re-enrolment. Treat `identify` as recognition against the *user-provided enrolled template gallery*, not a permissive generic fingerprint detector. Correct matching means one hardware touch, both saved templates considered, true `MATCH` only when the protected MOH matcher returns `MATCH` against one stored template.

**Verified code/API facts:**
- Every existing GitHub branch inspected (`main`, `feature/ft5955-relay-latency`, `feature/ft5955-timingtrace`, `feature/ft5955-driver-consolidation-20261017`, KDE branch) has the same immutable **16 October** snapshot `ft5955_native_action.c` (Git blob `25e39c29ba9ab3edc42a9d8b4ad077c295fdc145`); it **does not** contain the `FT5955TIMING` log markers observed in the running driver. Hence GitHub snapshot **is not established to be equivalent to the currently installed source**. Do not overwrite a live checkout or install a fresh rebuilt snapshot blindly: it risks regressing proven worker cancellation and timing.
- The snapshot's class only registers `dev_class->enroll` and `dev_class->verify`; registering `dev_class->identify` triggers libfprint automatic feature detection but requires an actual identify worker.
- libfprint internal API: `fpi_device_get_identify_data(device, &prints)` gives a GPtrArray of enrolled `FpPrint` gallery entries; results are reported with `fpi_device_identify_report(device, matched_gallery_print, scanned_print, error)` then `fpi_device_identify_complete`. Ordinary user `verify` still follows its own existing callback.
- Current MOH protocol `MODE V <size> <subfactor>` imports **one** stored print per gateway session, then `FRAME` examines a capture. Correct identify implementation must capture **once**, retain the same image for all enrolled gallery entries, and use separately initialised protected matcher sessions to test each print until first real MATCH. **NO_MATCH** continues through the gallery; an invalid template, backend timeout or IPC error must fail closed, not become an authentication success. A `RETRY QUALITY` must not be silently transformed to MATCH or bypassed.
- Copy/extract gallery templates on the libfprint main context and hold a reference to any matched `FpPrint` until reporting; never log images/templates; wipe frame buffers after use. Do not allow empty gallery to imply auth success. Maintain cancellation bounds and existing checked relay. Match only prints passed by libfprint/fprintd for the current user.
- **First implementation step:** obtain a **read-only source/runtime comparison** from the existing `~/Projects/libfprint-ft5955` checkout for `focaltech_5955.c`, `ft5955_native_action.c` and `ft5955_native_action.h`. Do not reset/clean dirty worktrees. Then implement and compile using the actual current source, preferably an opt-in test against the existing branch/build path; only stage/install with guarded backup and rollback after code/API tests. Preserve protected UID955 service and global PAM.
- This is a newly authorised extension; do not reopen solved latency, USB, or enrolment baselines.

## 19 OCTOBER 2026 — KDE screen unlocking works with global fingerprint PAM

- **User explicitly confirms successful KDE screen unlocking using a fingerprint**, after global `authselect with-fingerprint` activation and successful real `pkexec` / `sudo` fingerprint authorisation. This is a new live result and supersedes older statements that KDE unlocking remained untested after PAM activation.
- The user did **not** specify which finger unlocked the screen, how many lock/unlock repetitions were tested, or whether password unlocking was separately checked *after* activation. Do not invent these details. The earlier `sudo -v` password login did succeed after activation, and Ctrl+C was user-confirmed to switch sudo from fingerprint to password.
- **Operational milestones now achieved:** libfprint capture, fingerprint enrolment, protected MOH matcher, real fprintd verification, socket automatic startup after reboot, global authselect PAM activation, real Polkit/sudo fingerprint authorisation, and KDE screen unlocking.
- **Remaining before a maintained release:** accept either enrolled index finger through proper libfprint `identify` (current `any` falls back to right-index `verify`); assess the earlier intermittent `AlreadyInUse` claim symptom without inventing a proven cancellation bug (latest 12:00:31 cancellation fully cleaned up); consolidate source vs installed driver, guarded install/recovery and eventual retirement of `-dev` names; resolve/properly disclose MOH template authenticity, identity binding and vendor sandbox risks. Preserve global PAM backup `ft5955-pre-fingerprint-20261019-113538`, current working setup and password fallback. Do not repeat successful basic matching/latency tests.

## 19 OCTOBER 2026 — cancelled verification cleanly completes; Ctrl+C switches sudo to password

**Important correction to earlier diagnosis:** User reports that, while `sudo` requests a fingerprint, **Ctrl+C cancels the fingerprint authentication attempt and allows password entry without waiting for its timeout**; this workflow works on the user's actual host. Earlier advice implying Ctrl+C always cancels all of `sudo` was too broad. **Ctrl+Z** suspends the foreground task and should not be used as the password-switch mechanism.

Read-only host observations:
- `systemctl show fprintd.service` returned `ActiveState=inactive`, `SubState=dead`, `Result=success`, `TimeoutStopUSec=45s`. On-demand daemon inactivity is not an error.
- At 12:00:04–12:00:07 in the current boot journal, two `matcher_no_match` and one `matcher_match` operations completed with `verify_finish_done`, confirming a functional matcher at that time.
- At **12:00:27** a new verification reached `gateway_ready`. At **12:00:31**, the journal recorded `Verification was in progress, stopping it`, then `cleanup_begin`, `gateway_wait_complete`, `worker_return`, `verify_finish_start`, **`verify_finish_done`**, all in approximately **20.4 ms** from cleanup begin to verified finish. `fprintd.service: Deactivated successfully` followed at **12:01:01**.
- Therefore **this most recently logged cancellation completed normally**. It does **not** reproduce an incomplete libfprint cleanup. Earlier `AlreadyInUse` errors remain documented facts, but attributing them conclusively to a cancellation-handler bug was premature; a previous outstanding D-Bus claim or suspended client remains possible, cause unproven.
- Previous `systemctl restart fprintd.service` command took **45.495 s** and service stop timeout was `45s`, suggesting a stop-timeout interaction but not proving one from the displayed journal excerpt. Inspect only if the slow restart or `AlreadyInUse` returns; do not alter already-verified relay timing or USB polling.
- `sudo -v` previously accepted a password immediately; `sudo -n systemctl restart fprintd.service` then succeeded. The source/staged authselect rollback backup remains `ft5955-pre-fingerprint-20261019-113538`.

**Next:** retain normal global fingerprint PAM, use Ctrl+C for password fallback at a fingerprint-first sudo prompt as user-verified, and continue the outstanding KDE locker and multi-finger `identify` integration. Avoid unnecessary service restarts and repeated completed tests. Leave the experimental privileged-matcher security review and `-dev` retirement on the release checklist.

## 19 OCTOBER 2026 — sudo password fallback and fprintd restart succeeded

- User tried `sudo -n systemctl restart fprintd.service`; it correctly refused: `sudo: a password is required`, because there was no cached authorisation.
- In a fresh terminal, `sudo -v` **immediately prompted `[sudo] password for tim:`**, accepted the user's password and succeeded in **3.464 s**. This is positive evidence that password fallback remains accessible with global `with-fingerprint` enabled when the sensor is already claimed.
- Immediately afterward `sudo -n systemctl restart fprintd.service` returned **success**, but the shell recorded **45.495 s**. Treat this unusually long restart as an important cancellation/teardown clue, not as proof of the cause. There is no new `fprintd-verify` success report yet after the restart.
- **Next:** inspect *current* `fprintd.service` journal entries associated with restart (read only), plus service state. Look for systemd stop timeout, failed worker cancellation/cleanup, or a stuck client. Do not change PAM or the validated MOH service, and do not repeat general matching/timing tests. After diagnosing shutdown, check that the fprintd claim is cleared using the narrowest safe path.
- Separate remaining issues: both-finger `identify` support; KDE screen unlock; maintained non-`dev` service; previously documented proprietary matcher security checks. Preserve authselect backup `ft5955-pre-fingerprint-20261019-113538` and password fallback.

## 19 OCTOBER 2026 — fingerprint verification cancellation/claim leak observed

**Live host symptom:** After successful Polkit and sudo fingerprint PAM trials, user attempted sudo with a password instead of fingerprint and used Ctrl+C / Ctrl+Z, then closed the terminal. New user terminal showed no processes matching `[s]udo`. `ft5955-engine-dev.socket` remained `active`. `fprintd-verify -f right-index-finger` immediately returned `GDBus.Error:net.reactivated.Fprint.Error.AlreadyInUse: Device was already claimed`.

**Relevant fprintd journal evidence:**
- Earlier completed live verification attempts had `matcher_no_match` / `matcher_match`, `cleanup_begin`, `gateway_wait_complete`, `worker_return`, `verify_finish_start`, `verify_finish_done`.
- In the later incomplete attempt, `worker_start` → `scan_begin` → `gateway_ready` occurred, followed by `Verification was in progress, stopping it`, **without a visible `worker_return` or `verify_finish_done`**.
- At least six subsequent independent calls to `Claim` were rejected with `Device was already claimed`. `fprintd` itself remained running; only ordinary polkit daemon and KDE agent processes appeared in the filtered process listing (not evidence those two owned the claim).
- **Working hypothesis, not established root cause:** cancelled/incomplete verification or outstanding client claim left fprintd's device claimed; distinguish libfprint cancellation callback behaviour from a still-live client or fprintd state. Do not misdiagnose as MOH socket startup, USB driver damage or missing enrolment.

**Safe recovery recommendation issued:** first try `sudo -n systemctl restart fprintd.service` to avoid initiating fingerprint/password PAM while device already claimed. **Recovery not yet confirmed**. If `sudo -n` reports an authentication requirement, do not loop interactive sudo or make unmanaged PAM edits. Preserve the known authselect backup `ft5955-pre-fingerprint-20261019-113538`, password fallback and existing installed runtime.

**New completion criterion:** cancellation/timeouts/aborted sudo/Polkit PAM verification must release the device and permit the next operation, without restarting fprintd. Add a focused code/test inspection of cancellation and cleanup paths after recovering operation, not broad re-enrolment or speed tuning. This is a *separate, newly observed reliability issue*, not a return of the solved one-second relay teardown delay.

## 19 OCTOBER 2026 — real global PAM authorisation success

**User-confirmed live result:** After enabling `authselect with-fingerprint` (with preserved password profile and backup `ft5955-pre-fingerprint-20261019-113538`), the standard KDE Polkit request from `pkexec /usr/bin/id -u` **accepted the right index fingerprint**, and a separate **`sudo` authentication using the fingerprint also worked**. These are actual privileged PAM-path authentication successes through the current FocalTech driver and protected UID955 MOH service, not just `fprintd-verify` checks. The user's latest message does not include the exact `pkexec` output value, nor has password fallback been explicitly rechecked *since* global PAM activation.

**Known limitation:** Polkit prompts for the **right index** even though both right and left are enrolled; source snapshot registers `verify` but no `identify`. fprintd's `any` request selects one print for a verify-only driver. Investigate multi-template `identify` in the existing libfprint driver rather than changing PAM or re-enrolling. Retain the currently working service/driver, do not run repeat USB/timing baselines, and do not drop the final requirement to migrate from `-dev` service/path names.

**Remaining:** establish reliable KDE lock-screen authentication with password fallback; implement either-index-finger selection; review remaining MOH/template integrity and sandbox limitations before security signoff; consolidate a maintained non-`dev` installation with tested rollback. Successful Polkit and sudo tests prove functionality, **not** a complete security audit.

## 19 OCTOBER 2026 — multi-finger PAM selection gap

- After global `authselect with-fingerprint` activation, a live `pkexec /usr/bin/id -u` Polkit prompt asked specifically for the **right index finger**, although both left/right index fingers are enrolled and the left has verified explicitly.
- Inspected GitHub historical driver source `driver/live-snapshot-2026-10-16/libfprint/drivers/focaltech_5955.c`: `dev_class->scan_type = FP_SCAN_TYPE_PRESS`, `dev_class->enroll = ft5955_native_enroll`, `dev_class->verify = ft5955_native_verify`, but **no `dev_class->identify`** callback is registered in this snapshot. The installed library has not been directly compared against this source at this checkpoint.
- Upstream fprintd 1.94.5 `pam_fprintd.c` invokes `VerifyStart("any")`, but the D-Bus interface only selects *all enrolled fingerprints* if a device supports multi-print identification; otherwise it chooses a specific available finger. Current right-index prompt is consistent with **verify-only** driver capability; it does not establish that the left enrolment disappeared.
- **Required for the finished driver:** implement a proper `libfprint` multi-template **identify** operation in the existing driver without repeat enrolment or a new driver/service architecture, using one real capture per authentication and checking templates for only the claimed user; report success/failure through the usual libfprint callbacks, preserving bounds, cancellation, user binding and fail-closed handling. First reconcile the installed driver with source before editing; use existing tests and safe integration workflow.
- Do NOT modify PAM, manually relabel fingerprints, delete/redo enrolments, or patch fprintd to force a finger. The current right-index Polkit prompt is evidence of global PAM wiring, not yet confirmation that `pkexec` succeeded.

## REMAINING — only the actual project work

1. **Confirmed on the live host:** corrected relay installed with backup, development MOH socket restored to active, end-to-end verification regained, and the final seven left-index checks after user re-enrolment all returned MATCH. No more verification baseline work for this milestone. Check only the socket's reboot activation policy before consolidating the maintainable install/rollback instructions.
2. Consolidate the existing working libfprint driver, build/installation/rollback and documentation into a maintainable project state, using existing Linux services.
3. Record realistic operating/security limitations without endlessly introducing new subsystems. Keep normal password authentication available.
4. Later, as a separate explicitly authorised phase, build a **native Linux fingerprint matcher** to remove the proprietary Windows MOH dependency.

## NEXT ACTION

**The user has now confirmed real KDE screen fingerprint unlocking, plus successful global Polkit and sudo fingerprint authentication. Do not repeat their completed functional tests.** Focus next on adding multi-template `identify` support to the existing `focaltech_5955` libfprint driver so the `any` PAM request recognises either enrolled index finger, using a read-only source-vs-installed driver comparison before modification. In parallel, keep the originally requested maintained non-`dev` installation/rollback work and remaining MOH identity/template/sandbox security review on the release checklist. Preserve the working daemon, password fallback and named authselect backup; do not create a second architecture or touch unrelated PAM settings.

At the start of each new chat, read this file and report **COMPLETED / REMAINING / NEXT ACTION**. Never silently convert a hypothesis into a fault or repeat earlier testing. Update this file when a significant result changes the project state.

## Historical evidence

- `docs/next-session-handoff.md` — original lab and timing experiments; contains **dated historical snapshots**, not necessarily current state.
- `docs/kde-short-lived-trial-2026-10-17.md` — both fingers enrolled, matching and initial rollback.
- `docs/ft5955-dev-real-service-handoff-2026-10-18.md` — actual dedicated-service verification match.
- `docs/roadmap.md` — milestones and archive; read dated statements in chronological context.

**Conflicts in historical documents must be reconciled by newer user-observed facts and real code/deployment evidence, not by adding another experiment.**
