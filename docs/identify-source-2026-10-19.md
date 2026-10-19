# FT5955 two-finger identification: opt-in source-only implementation

**19 October 2026.** The user wants standard PAM \`any\` to accept either enrolled index finger without another enrolment. This is the *existing* \`focaltech_5955\` libfprint driver; the proprietary MOH engine, UID955 service and global PAM stay untouched while this source variant is evaluated.

## Source of truth and non-regression

User's read-only SHA-256 output for the three local \`~/Projects/libfprint-ft5955\` files exactly equals the immutable 16 October GitHub source manifest:

- \`focaltech_5955.c\`: \`40418e509506400a4118a35f76a0482ad614b855d285d88971e342b81ebad703\`
- \`ft5955_native_action.c\`: \`0f52c8de56f4ee524f1225bd0db559262505c21f906b4034def1e01d61ec94ab\`
- \`ft5955_native_action.h\`: \`4c7098d939e792540d82320dd9bcf2eb5899dec9571cc8172d22b9541c5629ee\`

The active \`/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0\` contains \`FT5955TIMING phase=%s mono_us=%li\` — instrumentation **absent from those source files**. The installed library came from an opt-in disposable-build transformation on the relay-latency branch. A direct rebuild from \`~/Projects/libfprint-ft5955\` would therefore regress the running driver and is prohibited.

## Opt-in changes committed on this existing branch

- \`tools/ft5955_identify_overlay.py\` adds \`dev_class->identify\` and a separate async identify worker **only inside a disposable reconstructed upstream libfprint source**. No immutable driver snapshot or installed source file changes.
- \`tools/verify_ft5955_clean_clone.py --build --trace-timing --identify\` compiles the previous validated 100-ms, early-capture, trace variant with this overlay. \`--stage --trace-timing --identify\` additionally stages the resulting library in private \`~/.local/state/ft5955-system-trial/stage-identify\` but **does not install it**. The existing privileged install script has no identify activation option.
- \`tests/test_ft5955_identify_overlay.py\` asserts registration, a single capture before a gallery search, no-match safety, unchanged verify callback, bounded retries, snapshot immutability and fail-before-write source preflight. An existing GitHub Actions offline synthetic workflow now includes these tests. **Test source contracts are not proof of real-device identification.**

Implementation uses \`fpi_device_get_identify_data()\` to obtain only libfprint-provided enrolled prints. It validates/extracts each vendor template, copies and later clears the protected bytes, captures one new finger touch, then starts one protected \`MODE V\` gateway per gallery entry using **the same captured image**. A vendor \`MATCH\` maps to the corresponding original \`FpPrint\`; genuine \`NO_MATCH\` proceeds to the next entry; quality reject requests a *fresh* touch; malformed result, backend failure, invalid template, cancelled request, forced gateway kill or empty gallery **fail closed**. No raw images or templates logged. Only the existing vendor matching process determines MATCH. Explicit \`verify\` and \`enroll\` callbacks remain unchanged. A scanned print FpPrint is not synthesized (the vendor engine provides only a verdict); libfprint match callbacks permit it to be omitted for this kind of device.

## Gates before installation

1. Run the offline source tests (NO USB), then the opt-in clean build (NO USB, NO privileged install) from the **existing relay-latency checkout** after a clean fast-forward update; do not overwrite a dirty checkout or create new worktrees.
2. Resolve compiler warnings or API mistakes against exact pinned libfprint \`v1.94.100\` headers. The resulting code is currently **uncompiled on the user's machine**, and the source-only commit is not a pass claim.
3. Prepare a guarded installation plan with an exact backup of the *currently loaded* \`/opt/ft5955-system-trial/lib\` and rollback independent of PAM; user approval is required to replace the live auth library. No changes to enrolled prints or credential files.
4. Confirm single-touch matching both left and right fingers, wrong-finger rejection, interrupted/timeout cleanup, normal password fallback and no \`AlreadyInUse\` regression in a controlled session.
5. Preserve the long-term non-\`dev\` service migration and proprietary MOH trust review; identify is not itself an authentication-security audit.

**Scope:** no PAM edits, no new branch, no changes to the already hardware-tested timing/relay source, no biometric captures during source or build tests.

## Confirmed read-only build result — 19 October 2026

**User's real Nobara output** from existing checkout `~/Projects/ft5955-relay-latency-test` (detached HEAD fast-forwarded successfully from `66e054c` to `ccfdd59`):

- `python3 -m unittest discover -s tests -p test_ft5955_identify_overlay.py -v`: **4/4 PASS**, 0.002 seconds. Tests cover overlay anchors, no changes to historical snapshot, no repeat apply, symlink rejection.
- `python3 tools/verify_ft5955_clean_clone.py --build --trace-timing --identify`: historical patch digests verified; exact upstream libfprint `v1.94.100` Git commit `80a4b5ec612892c5c056c48dddaa561452cf37ec`; all three patches applied; 100 ms polling + early-capture + nonbiometric timing trace + identify overlay applied in a disposable /tmp source; Meson 27 build targets; Ninja **109/109 PASS**; output `PASS: CLEAN upstream clone + 3 GitHub patches built independently`, followed by `PASS: disposable source and build removed; live driver, system fprintd, PAM unchanged.`
- Annotated-tag warning and skipped optional introspection-dependent tests were nonfatal. **A full runtime test suite, staging, installation and genuine two-finger identify are not yet proven.** No hardware or enrolment was accessed during build.
- The existing `tools/ft5955_kde_trial.sh` / `manage_ft5955_kde_trial.sh` are historical short-lived trial launchers, and the latter explicitly refuses activation when `fprintd-pam` is present. **Do not use them to bypass guards in this now-functional global PAM setup.** After staging, a purpose-designed reversible live installation test is needed to preserve current `/opt` driver and enrolled templates.

**Next safe step**: `python3 "$HOME/Projects/ft5955-relay-latency-test/tools/verify_ft5955_clean_clone.py" --stage --trace-timing --identify`. This will perform another isolated compile and place a user-owned output under `~/.local/state/ft5955-system-trial/stage-identify`, refusing overwrite if it exists; it will not change running `/opt` libfprint, PAM, system fprintd, MOH service or user templates. Then validate the staged SHA-256 and plan guarded backup/rollback for a real test; no direct copy into /opt and no reliance on deprecated trial launchers.


## User-verified identify staging PASS — 19 October 2026

The user's real Nobara terminal run of `python3 "$repo/tools/verify_ft5955_clean_clone.py" --stage --trace-timing --identify` completed successfully in ~4.4 seconds. GitHub snapshot source/patch manifest verified; upstream pinned libfprint v1.94.100 at `80a4b5ec`; Ninja **109/109**; the private staged library was written to `/home/tim/.local/state/ft5955-system-trial/stage-identify/lib/libfprint-2.so.2.0.0`. Staged SHA-256 reported: **`70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd`**.

The variant's own output explicitly confirms **nothing installed under `/opt`, `/etc`, or `/usr`**, and no USB, system fprintd or PAM operations. Original active library remains unchanged. No real identification performed yet. The optional introspection-dependent tests were skipped at Meson configuration and are **not** counted as passing.

**Next immediate check, read-only:** verify the staged `SHA256` manifest and file with `sha256sum -c`, record checksum and physical ownership/type of the current `/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0`, check `fprintd.service` drop-ins and live paths, then prepare reversible, guarded live swap without touching `fprintd-pam`, `authselect`, global PAM, MOH, daemon configuration or prints. Existing lab install wrappers refuse when fprintd-pam is active and must not be reused or guard-bypassed. Never blindly overwrite current binary or delete historic staged libraries.


## Verified stage integrity and live binary fingerprint — 19 October 2026

User's **read-only** Nobara preflight confirms staged `sha256sum -c SHA256` returned `lib/libfprint-2.so.2.0.0: OK`. Candidate in `/home/tim/.local/state/ft5955-system-trial/stage-identify/lib/libfprint-2.so.2.0.0`: SHA-256 `70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd`, owner `tim:tim`, mode `0600`.

The **currently installed working** `/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0` is SHA-256 `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`, owner `root:root`, mode `0644`. `fprintd.service`: `ActiveState=inactive`, `MainPID=0`, and active unit configuration includes `/usr/lib/systemd/system/service.d/10-timeout-abort.conf`, `/etc/systemd/system/fprintd.service.d/90-ft5955-system-trial.conf`, plus a `95-…` drop-in (terminal output truncated; need full value and file contents before any guarded live swap). No biometric testing yet.

**Next action**: inspect full installed service overrides, original marker file and any existing root-owned backup without making changes. Build a **dedicated guarded installer/rollback** that verifies these exact two hashes, snapshots the current live binary before any modification, refuses conflicting/busy states and unexpected ownership, uses atomic replacement under the same filesystem, records marker changes only if required, and makes rollback possible using password fallback even when fingerprint scanning is unavailable. Do not reuse old lab install scripts; preserve live UID955 matcher socket, PAM, current fingerprints and auto-activation.


## Read-only service inspection and guarded live trial script — 19 October 2026

User provided `systemctl cat fprintd.service` and original owner marker. The active unit has two experimental files:

- `/etc/systemd/system/fprintd.service.d/90-ft5955-system-trial.conf`: `LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib`, `FT5955_EXPERIMENTAL_ENABLE=1`, and an older initial relay path that the later override supersedes.
- `/etc/systemd/system/fprintd.service.d/95-ft5955-moh-dev-gateway.conf`: the **effective** `FT5955_ENGINE_GATEWAY=/opt/ft5955-dev/ft5955_dev_relay.py` to the protected UID955 MOH server.
- Original `/opt/ft5955-system-trial/FT5955_TRIAL_OWNER` contains `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`, exactly the **original live library** hash. Existing `fprintd.service` was inactive, PID0.

Prepared [`tools/ft5955_identify_live_trial.sh`](../tools/ft5955_identify_live_trial.sh) in the already existing relay-latency branch with `--status` (read-only), `--activate` and `--rollback`. **Not yet executed, tested by user, or activated.** It guards the specific known-good and staged candidate SHA-256 values, original root file/SONAME layout, root-owned 90-/95- overrides and actual systemd environment, candidate manifest and user ownership/mode, and requires inactive fprintd before modifying its binary. On activation it creates a root-only `/opt/ft5955-system-trial/.identify-rollback-20261019` backup of the original library and checksum marker, verifies the backup before atomic same-filesystem file/marker renames, and leaves enrolled prints, MOH service, global PAM, authselect and unit files untouched. Rollback uses the **retained backup** even if the staged candidate disappears or marker update was partially completed. The script does **not** start or stop system services; these states are checked before swapping. The old trial installer is not used.

Added `tests/test_ft5955_identify_live_trial.py` and extended the existing GitHub Actions synthetic workflow to run `bash -n` and offline source-contract tests without root or hardware access. **Do not claim those have passed until observed**. Static tests do not prove the privileged live swap is correct; the user must inspect its read-only preflight before activation.

**Next user terminal step (safe):** Fast-forward the existing detached-HEAD `~/Projects/ft5955-relay-latency-test` checkout **only if clean**, then execute `bash -n tools/ft5955_identify_live_trial.sh` and `python3 -m unittest discover -s tests -p test_ft5955_identify_live_trial.py -v`. If those pass, run `sudo -n bash tools/ft5955_identify_live_trial.sh --status` (after obtaining a normal password sudo ticket if needed); inspect output before enabling `--activate`. No additional enrolment or PAM alteration.


## User-verified guarded installer read-only --status — 19 October 2026

The user invoked `sudo bash tools/ft5955_identify_live_trial.sh --status` and authenticated via a **right-index-finger** fingerprint prompt. The read-only output was:

```
LIVE_SHA=02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28
MARKER_SHA=02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28
ROLLBACK_BACKUP=not-yet-created
FPRINTD_STATE=active
READ ONLY: no changes
```

**Interpretation:** Current installed lib and checksum owner marker exactly match the original known-good baseline; no earlier trial backup conflict. `fprintd` was active *because sudo's successful fingerprint authorisation started it*. This is not a driver regression. The `--activate` script intentionally **refuses to swap while fprintd is active**. Do not restart it, change PAM or bypass the safety guard. Use an existing sudo authentication ticket with **`sudo -n`** to avoid another fingerprint scan, wait for fprintd's idle auto-deactivation with a bounded, read-only poll, then invoke guarded `--activate` only if inactive. If no cached sudo ticket or still-active fprintd, stop safely and re-evaluate. **No live swap has yet occurred.**


## Guarded identify activation success — 19 October 2026

**User terminal reports successful guarded activation** with a cached non-interactive sudo credential after waiting for `fprintd.service` to become inactive. Actual script output:

```
PASS: original root-owned library and marker securely backed up.
PASS: identify library selected for the next on-demand fprintd start.
PAM, both service overrides, protected MOH and enrolled prints unchanged.
ROLLBACK: sudo -n bash /home/tim/Projects/ft5955-relay-latency-test/tools/ft5955_identify_live_trial.sh --rollback
```

The installer reported making and checking a root-owned backup before replacing the experimental shared library and owner marker. **This confirms script-reported activation, not real identify behaviour**. Next read-only `sudo -n bash tools/ft5955_identify_live_trial.sh --status` should independently report `LIVE_SHA` and `MARKER_SHA` of `70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd` and `ROLLBACK_BACKUP=verified`. This status command does not restart fprintd, change authentication or touch the fingerprint sensor. If noninteractive sudo expired, status must fail rather than prompt fingerprint again. After confirming status, proceed to one controlled identify test, not fresh enrolment. Roll back on any abnormal denial, hang or wrong match; use password authentication to obtain root access if necessary, preserving the known-good SHA `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`.

## Successful independent installed-hash and backup readback — 19 October 2026

The user ran `sudo -n bash tools/ft5955_identify_live_trial.sh --status` **after** activation. Reported results:

```
LIVE_SHA=70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd
MARKER_SHA=70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd
ROLLBACK_BACKUP=verified
FPRINTD_STATE=inactive
READ ONLY: no changes
```

**Confirmed:** active candidate and marker are the exact verified build; known-good baseline backup and marker passed guard verification; fprintd is stopped, so the next verification will activate a new process loading candidate. No hardware identify test yet, and not evidence either enrolled finger works under `any`. **Next:** run a single `fprintd-verify -f any` as normal user, deliberately press the **left** index finger first (previous driver only selected right for `any`); log `verify-match` / `verify-no-match`, hangs and any errors. If a failure occurs, do not launch repeated scans or use sudo repeatedly; inspect filtered diagnostics and roll back with the guarded script after inactive fprintd. Neither PAM nor enrolled data should be edited. The fprintd D-Bus `VerifyStart("any")` specification permits gallery search when the device supports identification.

## Real both-finger recognition; timing and gallery-quality issues — 19 October 2026

User reports `fprintd-verify -f any` **eventually recognised both enrolled left and right index fingers**, but is slower and seems less consistent than earlier single-finger verification. The normal fprintd CLI reported authentication result without the name of which enrolled finger matched. This is a *functional observation*, **not** a validated matched-finger mapping or false-accept/false-reject rate.

**Source audit (existing installed candidate SHA `70609faa6783d917...`):**

1. `ft5955_identify_worker()` sends one captured frame serially to `ft5955_identify_try()` once per gallery candidate. Each candidate launches a fresh `MODE V` protected gateway process, initializes the MOH matcher and then executes bounded process cleanup **before trying the next template**. This extra start/stop overhead was not present in single-template `verify`.
2. Previous verified early-capture performance improvement (starting matcher setup concurrently with USB finger monitoring) exists **only in `verify`**. Our new `identify` starts candidate #1 matcher **after** image acquisition. This is a likely new latency source, independent of the already-fixed 1-second Python broker join.
3. The current identify path treats a single candidate `RETRY QUALITY` as an immediate `break` from the gallery, requiring a new touch **before remaining enrolled candidates can be checked**. If quality rejection is template-dependent, this introduces avoidable retry/false-rejection behaviour, especially for the later gallery template. The correct candidate-independent decision must be verified against MOH semantics; no relaxed MATCH thresholds should be introduced.
4. `FT5955TIMING` markers instrument `verify`, **not the separate identify worker**, so their absence during `any` cannot establish which step caused delay. Instrument future identify candidate startup/response/cleanup with event-only monotonic timing markers; never log raw frames, templates, finger labels or user identities. Existing `g_subprocess_get_identifier` timeout loops also merit review, but measured 10-second stalls are **not** confirmed.

**Safe priority:** The current identify candidate is active in global PAM and is user-reported slower/less consistent. Prefer using the already verified known-good rollback `tools/ft5955_identify_live_trial.sh --rollback` during offline work; its safety guard requires inactive fprintd and validated exact original root-owned backup, and `sudo -n` avoids triggering a new fingerprint prompt when credentials are cached. Retain existing saved templates and both systemd overrides. Before another live candidate: correct gallery RETRY handling, recover concurrent startup timing, add event-only timing traces, compile/test offline, stage as a *new* artifact (never replace previously verified SHA or untracked local source), and validate negative/wrong-finger results in a controlled trial. No patch or rollback is yet deployed as a result of this audit.

## Verified restoration after first identify performance trial — 19 October 2026

User ran the existing guarded `sudo -n .../tools/ft5955_identify_live_trial.sh --rollback` after allowing `fprintd.service` to deactivate. Real terminal result:

```
PASS: original known-good libfprint and original marker restored.
```

The script's known-good checksum guard was expected to restore binary/marker SHA-256 `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28` from the earlier root-only verified rollback directory, leaving all enrolments, protected MOH service, systemd overrides and PAM unchanged. **No independent post-rollback `--status` readback has been reported yet.** The trial demonstrated both fingerprints eventually recognised using `any`, but with worse latency and consistency than the previous baseline. Do not treat a successful rollback exit as measured matching performance.

**Source development next:** preserve the already compiled/staged v1 identify candidate (SHA `70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd`) for forensic reproducibility. Develop new v2 as a separate disposable overlay and separately named stage; specifically avoid cutting off remaining gallery entries on quality-retry and add non-biometric identification timing to see per-template gateway startup/matching/shutdown. Start/verify timing optimisations only once the event trace isolates delays; the current old `verify` early-capture path remains known good. No changes to live authentication during development.


## Source-only identify v2 quality/diagnostic overlay — 19 October 2026

After the known-good live rollback, implementation is proceeding **exclusively on the existing `feature/ft5955-relay-latency` branch**; the current original driver in `/opt`, global PAM, MOH service, saved templates and prior v1 identify stage all remain untouched.

- Added `tools/ft5955_identify_overlay_v2.py`, applied **after** historical `apply_identify_variant` on a disposable, SHA-verified libfprint source. This ensures the old `--identify` build continues to reproduce its original checksum and behaviour.
- New gallery decision logic continues examining **all enrolled candidate templates against the same captured frame** after `RETRY QUALITY`, without relaxing what counts as `MATCH`. If no match but any candidate rejected quality, the worker waits for another *fresh* touch; it returns genuine NO_MATCH only when all templates returned NO_MATCH. It still rejects protocol failures and invalid templates.
- Added `ft5955_trace` **event-only** timestamps for identify worker/USB scan/capture/gateway process start+ready/reply/cleanup/decision/completion; no template IDs, user labels, images, frames or biometric materials printed. This is measurement instrumentation, **not** a claimed response-time improvement: the serial gallery matching sessions and lack of early-capture overlap are deliberately unchanged until hardware traces establish the actual bottleneck.
- The disposable builder accepts `--build --trace-timing --identify-v2` and can stage only under a **new** directory `stage-identify-v2`; it does not overwrite `stage-identify` and has no privileged installation option. `--identify` still selects the first version for reproducibility.
- Added `tests/test_ft5955_identify_v2.py` (source-contract, no USB, no enrolment) and existing GitHub Actions synthetic CI invocation. **Tests and compilation for v2 have not yet been user-reported and must not be claimed as passing**. Do not attempt a privileged v2 swap before source tests, build, trace/privacy review, stage SHA verification and a new independent rollback preflight.

**Next safe terminal action**: confirm restoration via `sudo -n bash "$HOME/Projects/ft5955-relay-latency-test/tools/ft5955_identify_live_trial.sh" --status` when a valid sudo ticket exists (no fingerprint prompt). Expected live and marker hashes start `02403d764535bc77`, original backup verified; if the ticket has expired, a normally authenticated `sudo` may start fprintd temporarily and should be treated as an observer only. Then perform a clean fast-forward of existing detached checkout to v2 commits, run its offline unit tests and source-only compile. **Do not install v2 yet**.

## User-confirmed identify v2 staging and separate guarded installer — 19 October 2026

**User-confirmed build and staging:** `python3 "$repo/tools/verify_ft5955_clean_clone.py" --stage --trace-timing --identify-v2` successfully verified original snapshot/three patches, rebuilt pinned upstream libfprint 1.94.100, compiled **109/109** targets, and staged to `/home/tim/.local/state/ft5955-system-trial/stage-identify-v2/lib/libfprint-2.so.2.0.0`. Reported **STAGED_LIB_SHA256**: `ad0ff83b5e515711eba822dc7ab69f24ab6f6c5764b0f5daed96a609c96666a9`. Historical v1 identify stage remains separate at `stage-identify`. The actual installed libfprint and marker had already been independently verified to be original SHA `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`. **No user hardware test of v2 or v2 install yet.** Missing optional introspection tests remain skipped, not passed.

New `tools/ft5955_identify_v2_trial.sh` has `--status`, `--activate`, `--rollback`; it pins v2 candidate SHA and original baseline SHA independently from historical v1 installer. It **requires** the already existing root-owned `/opt/ft5955-system-trial/.identify-rollback-20261019` backup from the first trial to pass its checksum, ownership and permissions checks; it never creates or overwrites that backup. Only root-owned experimental `/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0` and its existing SHA marker are eligible for atomic replacement. The v2 trial script checks the configured 90-/95- overrides, effective protected MOH routing and `fprintd.service` being inactive. Never use the v1 installer to roll back a v2 binary; use v2's exact installer and original backup. No PAM, `authselect`, enrollment records, sockets or vendor process modifications. A separate `tests/test_ft5955_identify_v2_live_trial.py` and existing offline GitHub Actions CI step check the new script's anchors and Bash syntax (not yet locally tested by the user).

**Next safe action:** update the existing clean detached-HEAD `~/Projects/ft5955-relay-latency-test` checkout with `git fetch` + `git merge --ff-only FETCH_HEAD`, run `bash -n tools/ft5955_identify_v2_trial.sh` and the new offline unit tests. If they pass, run `sudo -n bash tools/ft5955_identify_v2_trial.sh --status` only to verify the existing original backup and installed original checksum before any activation. Candidate v2's extra timing markers measure the serial matcher startup/teardown delay but **do not** yet fix it. Actual matched finger is not reported by standard `fprintd-verify -f any` CLI; do not log per-finger identifiers in journal timings.

## User-confirmed guarded identify v2 activation — 19 October 2026

User executed the dedicated `tools/ft5955_identify_v2_trial.sh --activate` after its read-only `--status` showed known-good live library SHA and marker `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`, `ROLLBACK_BACKUP=verified`, and `FPRINTD_STATE=active` (the activation command waited for inactivity). The installer reported:

```
PASS: pre-existing root-owned original libfprint and marker backup verified.
PASS: identify v2 library selected for next on-demand fprintd start.
PAM, both service overrides, protected MOH and enrolled prints unchanged.
ROLLBACK: sudo -n bash /home/tim/Projects/ft5955-relay-latency-test/tools/ft5955_identify_v2_trial.sh --rollback
```

**Exact v2 candidate SHA-256** `ad0ff83b5e515711eba822dc7ab69f24ab6f6c5764b0f5daed96a609c96666a9`, previously built with Meson/Ninja 109/109 and separately staged. This is installer-reported success; independent installed SHA readback and actual live identify timing measurements are **not yet reported**. **Next single step:** `sudo -n bash "$HOME/Projects/ft5955-relay-latency-test/tools/ft5955_identify_v2_trial.sh" --status`. Expect both candidate library and marker SHA equal to v2, plus `ROLLBACK_BACKUP=verified`. Before testing a finger, retain the root-only known-good backup; if hardware detection is unreliable, wait for fprintd inactive and use v2-specific `--rollback`. Do not use v1 installer for a v2 installation or modify saved fingerprints.

## User-verified v2 installation SHA and backup — 19 October 2026

User performed independent `sudo -n bash tools/ft5955_identify_v2_trial.sh --status` after guarded v2 activation. Exact readback:

```
LIVE_SHA=ad0ff83b5e515711eba822dc7ab69f24ab6f6c5764b0f5daed96a609c96666a9
MARKER_SHA=ad0ff83b5e515711eba822dc7ab69f24ab6f6c5764b0f5daed96a609c96666a9
ROLLBACK_BACKUP=verified
FPRINTD_STATE=inactive
READ ONLY: no changes
```

Candidate v2 and its marker therefore match the verified staged SHA. The root-owned original driver backup still passed integrity verification, and the service is idle ready to load v2 on demand. **No real v2 fingerprint match or speed result yet.** Next user test runs `fprintd-verify -f any` as ordinary user, intentionally left index first, followed by `sudo -n journalctl -b -u fprintd.service --since "$since" --no-pager -o cat | grep 'FT5955TIMING phase=identify_'`. The `since` time is recorded just before the single scan. This logs only event labels and monotonic timestamps; it does not record raw frames/templates. A silent journal command may indicate sudo cache expiry; report that limitation and do not infer absent timings.

## First real v2 identify trace: complete gallery NO_MATCH and 241ms after capture

User ran `fprintd-verify -f any` as an ordinary user after confirmed v2 install; fprintd listed gallery #0 right-index-finger and #1 left-index-finger. The single real verification terminated `verify-no-match (done)`. The event-only `FT5955TIMING phase=identify_*` journal from this run provides a complete TWO-TEMPLATE pass: first and second gateway start, ready, matcher reply, cleanup and final `identify_gallery_no_match`. No `identify_quality_retry` occurred. Thus **neither enrolled print matched this particular capture**; no evidence which physical finger was used beyond preceding instruction to use left index. One negative result does not measure overall accuracy or establish an identification defect.

| Monotonic phase interval | Measured |
| --- | ---: |
| identify_worker_start 11098815127 → identify_image_captured 11101446018 | **2630.891 ms**, includes initial scan waiting/physical finger placement, not pure driver latency |
| image captured → first gateway start | 0.016 ms |
| first gateway start 11101446034 → ready 11101540948 | **94.914 ms** |
| first ready → matcher reply 11101547635 | **6.687 ms** |
| first cleanup begin 11101547647 → done 11101567764 | **20.117 ms** |
| second gateway start 11101567793 → ready 11101659595 | **91.802 ms** |
| second ready → matcher reply 11101666395 | **6.800 ms** |
| second cleanup begin 11101666408 → done 11101686521 | **20.113 ms** |
| image captured 11101446018 → callback done 11101686716 | **240.698 ms** |
| worker start → callback done | **2861.589 ms** |

**Conclusion:** The previously eliminated ~1-second gateway cleanup delay is not recurring: each observed cleanup is ~20 ms. Both serial templates require only ~0.24 seconds total after image capture in this attempt. Most wall time (~2.63 seconds) was spent awaiting the first usable image and can include user placement time or release-to-contact polling. No reliable physical-press timestamp is present. **No MATCH so the first v2 hardware recognition test is a negative sample.** Next: controlled additional `any` attempt with **right index first** (gallery #0), repeat trace capture and distinguish success/no-match versus repeated quality. Then try left index independently after checking result. Preserve the active known-good backup and password fallback. Avoid premature optimisation of parallel gateway starts or old join; use observations first.

## Four left-index v2 trials and rollback recommendation

October 19 user-confirmed left-index trials: four consecutive `fprintd-verify -f any` results NO_MATCH, NO_MATCH, NO_MATCH, MATCH. Each NO_MATCH checked two gallery candidates. The match occurred after checking the second candidate. No quality-retry event observed.

| Trial | Before image capture | Image to finish | Total |
|---|---:|---:|---:|
| No match 1 | 458.2 ms | 262.3 ms | 720.5 ms |
| No match 2 | 1235.4 ms | 266.4 ms | 1501.8 ms |
| No match 3 | 436.2 ms | 241.4 ms | 677.6 ms |
| Match 4 | 375.6 ms | 245.3 ms | 620.9 ms |

One match in four small, informal left-index trials is not a reliable statistical estimate but raises concern about consistency. Earlier one-template match was previously attributed to the right finger without confirmed gallery-label mapping; user clarification that tests involved the left finger makes that attribution unsafe. A one-template MATCH confirms the first candidate only, not independently its named finger. Before further live tests: recommend guarded v2 rollback while fprintd inactive and non-interactive sudo available, then audit actual gallery order and matching/cross-match behavior offline. Preserve protected matcher, PAM, prior staged candidate, timing logs and original enrollment records; do not tune acceptance thresholds.
