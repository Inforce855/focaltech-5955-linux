# Next-session handoff — FT5955 on Nobara

**Current checkpoint: 17 October 2026.** The real standard Linux/KDE enrol → verify → rollback experiment was **successful**. The experimental system installation is **not active** after the user-confirmed rollback. Treat this note as the starting point for the next development session, not as instructions to redo the completed tests.

## What has been demonstrated

- FocalTech USB **`2808:5955`**, built into the machine's power button; it **cannot be physically unplugged** as a convenient test.
- Private `fprintd` enrol/retry/reopen/cancellation, two negative-finger checks, stored-template restart roundtrip and direct USB capture have already been exercised. **Do not restart from those tests.**
- Reproducible upstream `libfprint v1.94.100` source reconstruction (pinned `80a4b5ec612892c5c056c48dddaa561452cf37ec`), three verified patches, Ninja **109/109** build steps. Compiled library staged under `~/.local/state/ft5955-system-trial/stage/` (it may remain) with SHA-256 **`003ed7e6d53109ad355b653f3b5a9a6cfb33c99e150ae5e58ed7f6ff41fd7d4e`**. A successful compile is *not* a full upstream test-suite PASS.
- **Normal** system `fprintd` loaded the experimental library and reported the device. The user started the short-lived user-session MOH/bwrap broker, and the actual KDE System Settings → Users interface displayed **Configure Fingerprint Authentication**.
- **Both left and right index fingers enrolled successfully in KDE.** Standard `fprintd-verify` subsequently produced real `verify-match` results. User estimates **about 85% match success after 3–4 rapid taps** (not a first-press estimate). **18 October clarification:** rapid tapping worked better than a single deliberate lift-and-press/hold; do not rephrase this as 'slow lift and press gives the best outcome'. Tapping does involve momentary separation but its short, repeated contacts may interact with the current polling/capture timing.
- `bash tools/ft5955_kde_trial.sh --stop` **PASSED** in the user's terminal: disabled the experimental gateway, removed the relay, dropped the dedicated `/opt` shared library and service override, and restored packaged Nobara `libfprint`/`fprintd`. **No PAM, SDDM or password-login changes.** The next normal activation was not independently mapped back to the package library, but the tested script confirmed rollback. A Timeshift snapshot was created before the trial; no restore was needed.
- Normal `fprintd` storage **may retain the two experimental enrolled templates** after rollback. That is separate from the staged local library and separate from the old private RAM-only templates.

## Current implementation layout

- **Current repository baseline:** **`main`** now contains the tested consolidation after [merged PR #4](https://github.com/Inforce855/focaltech-5955-linux/pull/4). The existing user checkout `~/Projects/ft5955-independent-build-check` tracks `feature/ft5955-driver-consolidation-20261017` and was **not silently switched to `main`** by the GitHub merge. Both branch histories are preserved. Check the local branch before updating or editing it; do not delete or rewrite the separate MOH/libfprint research checkouts.
- **Driver source of record:** [`driver/live-snapshot-2026-10-16/`](../driver/live-snapshot-2026-10-16/README.md), intentionally immutable due to checksum/patch provenance.
- **Clean upstream build and optional stage:** [`tools/verify_ft5955_clean_clone.py`](../tools/verify_ft5955_clean_clone.py).
- **System discovery-only install/rollback:** [`tools/manage_ft5955_system_trial.sh`](../tools/manage_ft5955_system_trial.sh).
- **Successful lab KDE start/stop:** [`tools/ft5955_kde_trial.sh`](../tools/ft5955_kde_trial.sh) and [`tools/manage_ft5955_kde_trial.sh`](../tools/manage_ft5955_kde_trial.sh); **not** a permanent installation/login setup.
- **User-session broker:** [`tools/ft5955_engine_broker.py`](../tools/ft5955_engine_broker.py), connecting normal root `fprintd` over a private AF_UNIX socket to the existing non-root MOH/bwrap process.
- **Existing MOH private loader:** expected at `~/Projects/focaltech-5955-moh-test`, with pinned Windows DLL at `/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll`. User's read-only audit confirmed the installed root-owned DLL matches its pinned SHA-256.
- **Exact experiment and rollback evidence:** [`kde-short-lived-trial-2026-10-17.md`](kde-short-lived-trial-2026-10-17.md).

## What to do next — ordered by value

1. **Investigate one-touch recognition first (source-reviewed 18 October):** [native capture code](../driver/live-snapshot-2026-10-16/libfprint/drivers/ft5955_native_capture.c) polls `0x82` status every **500 ms**, starts `armed=FALSE` and **requires an observed `0x06` (off)** before accepting `0x05` (on); it then waits only **10 ms** before a single `0x80` readiness query and the `0x81` image read. Brief taps/releases may be missed between half-second polls, and the 10-ms image timing may be too early for full contact. The readiness marker `0x5AA5` was previously observed even at idle; **it is not independently proven to mean a fresh stable image**. The `500 ms` value was inherited from the conservative **early** [automatic contact viewer](../tools/auto_contact_capture.py), not benchmarked for reliable KDE verification. **Test one change at a time:** a separate opt-in timing-only variant with ~100-ms status polling and the **same 120-second overall bound**, keeping all USB commands and the 10-ms post-detect delay otherwise unchanged initially. Investigate post-press settling *only if* contact-edge improvement is insufficient. Preserve the hash-pinned snapshot/patch-chain, use offline synthetic trace tests, and do not re-enrol merely to test timing. No hardware timing variant built/tested as of this note.
2. **Make authentication trustworthy before making it persistent.** The current MOH C compilation contains `FT5955_ALLOW_UNVERIFIED_ATTACH`; the backend is **owned by the login user** while normal `fprintd` runs as root, and the saved-template envelope uses unkeyed SHA-256 for corruption detection, **not authenticity**. These are actual architecture limitations for production login. Review secure matcher separation, origin/policy and storage, cancel/timeout, anti-spoof/false-accept measurement. **PAM still absent in tested environment** and must not be enabled merely because lab enrolment passed.
3. **Finish native matching** to remove the Windows MOH DLL dependency when validated, building on [`native/`](../native/README.md).
4. Prepare a maintained *reversible* package/installation path only after safety/reliability criteria. Preserve the known-good password login and original vendor libraries.

## 18 October — timing experiment prepared, not yet tested on sensor

The user clarified that **holding a finger continuously produced no apparent read**, and that **a deliberate lift, wait and press also tended to fail**, while **3–4 rapid taps** led to substantially more `verify-match` outcomes. This suggests a contact/rearm/capture timing problem, but terminal `verify-no-match` versus absence of any capture should be distinguished; the original user report does not prove the image was never acquired.

The **existing, immutable** `ft5955_native_capture.c` requires an observed OFF (0x06) → ON (0x05) edge, polls at **500 ms**, then sleeps **10 ms** before a single readiness check and image request. Holding the finger at verify start, without any observed OFF, will not trigger this code. The previously observed readiness value 0x5AA5 does **not** prove a fresh stable image.

A **separate opt-in 100-ms polling variant** is now supported by [`verify_ft5955_clean_clone.py`](../tools/verify_ft5955_clean_clone.py) using `--poll-100ms` alongside `--build` or `--stage`. It edits **only the disposable rebuilt source**, after verifying the original snapshot hashes. The polling cap changes from 240 to 1,200 (preserving the roughly two-minute wait), while USB command bytes, OFF→ON gate, 10-ms delay, image conversion and matcher remain exactly the same. An offline [source-transformation test](../tests/test_ft5955_poll_timing.py) passed in GitHub Actions. `--stage --poll-100ms` writes to **`~/.local/state/ft5955-system-trial/stage-poll100`** instead of overwriting the known-good `stage`.

The existing lab KDE wrapper accepts opt-in `--start-poll100`, which passes only the specifically permitted variant stage name through both reversible activation scripts. **`--stop` remains the same as the user-tested rollback.** This is a new path that has passed offline syntax and source checks but **has not been compiled on Nobara or tested with live fprintd/USB**. Do not enable PAM or automatically enrol more fingers. If the two KDE enrolments still exist after rollback, compare one or two normal `fprintd-verify` results, especially whether it says `verify-no-match` or waits indefinitely. Only consider changing the 10-ms post-contact delay **later**, if 100-ms contact polling is insufficient. Do not claim improved recognition without the user's real test.

**Build/stage preparation (normal user, offline except upstream source fetch):**

```bash
REPO="$HOME/Projects/ft5955-independent-build-check"
# Original checkout has local changes; DO NOT switch, reset or stash it.
# origin/main was already fetched into the original checkout.
TEST="$HOME/Projects/ft5955-poll100-build"
git -C "$REPO" worktree add --detach "$TEST" origin/main &&
python3 "$TEST/tools/verify_ft5955_clean_clone.py" --stage --poll-100ms
```

This neither installs nor operates the fingerprint reader. Only after this build passes should the user elect to run `bash "$REPO/tools/ft5955_kde_trial.sh" --start-poll100`; the rollback is `bash "$REPO/tools/ft5955_kde_trial.sh" --stop`. Neither command changes PAM. The existing staged baseline binary and source checkout remain preserved.

## 18 October — separate 100-ms variant independent build: PASS (user terminal)

The first attempt to switch the single-branch `~/Projects/ft5955-independent-build-check` checkout to `main` failed: it had no local `main` reference; a second attempt failed safely because locally modified `docs/next-session-handoff.md` would have been overwritten. **No changes were discarded.** Instead, the user created a separate detached Git worktree at `~/Projects/ft5955-poll100-build` tracking the fetched `origin/main`, and ran:

```bash
python3 "$HOME/Projects/ft5955-poll100-build/tools/verify_ft5955_clean_clone.py" --stage --poll-100ms
```

**User-reported PASS:** Meson 27 targets, Ninja `[109/109]`, pinned upstream + all 3 verified patches, isolated source adjustment, and independently compiled staged library at `/home/tim/.local/state/ft5955-system-trial/stage-poll100`. **SHA-256 `8deff4de7a1d7e85cae0dbfd415e388d76347d1e61e85a6fe2fa4e241aedd8ec`.** The disposable source was cleaned automatically; original `stage`, normal packaged libfprint/fprintd and PAM were unchanged. This confirms **build/stage only**, not improved sensor recognition.

**Next opt-in real trial**: `bash "$HOME/Projects/ft5955-poll100-build/tools/ft5955_kde_trial.sh" --start-poll100`. The **unchanged rollback** is `bash "$HOME/Projects/ft5955-poll100-build/tools/ft5955_kde_trial.sh" --stop`. After successful activation, compare a small number of deliberate single presses using previously enrolled fingers with `fprintd-verify -f left-index-finger`, checking whether it waits, retries or emits `verify-no-match` / `verify-match`. No re-enrolment, PAM changes, driver-flashing or matcher changes. New 100-ms activation is **not yet hardware-tested** at this checkpoint.

## 18 October — REAL 100-ms system KDE verification timing comparison (user-reported)

**Activation PASS:** The first `--start-poll100` attempt stopped at the existing fprintd preflight guard because normal `fprintd` was already running; its cleanup confirmed no experimental installation remained. After the user explicitly ran `sudo systemctl stop fprintd.service`, `bash "$HOME/Projects/ft5955-poll100-build/tools/ft5955_kde_trial.sh" --start-poll100` **PASSED**. The new staged SHA-256 `8deff4de7a1d7e85cae0dbfd415e388d76347d1e61e85a6fe2fa4e241aedd8ec` was verified; normal fprintd initially mapped the experimental .so (PID 61087) and restarted with the working lab bridge (PID 61263), and the standard system D-Bus manager returned a fingerprint device. No PAM changes. A subsequent `systemctl show` reported `ActiveState=inactive`, `MainPID=0` while the experimental drop-in still existed. This is compatible with an idle D-Bus-activated fprintd service; do not treat it as proof the experimental override vanished.

**Actual user-reported behavioural comparison with this new 100-ms version:**

| Finger action relative to `fprintd-verify` prompt | Informal outcome |
| --- | --- |
| Wait for verify message, then press/hold | **~80% failures or no apparent capture** |
| Wait an additional ≥1 second after message, then press/hold | **~30% failures**, sometimes a long wait |
| Immediately tap **2–3 times per second** after message | **~95% success within 1–2 seconds** |

Sample counts and the precise terminal messages on the failing cases were not captured. Percentages are informal observational estimates, **not a statistically controlled acceptance/error benchmark**. Earlier 500-ms trial had an approximately **85% multi-tap success** observation using 3–4 taps; the reported ~95% success in the 100-ms trial is encouraging but not a controlled one-variable recognition accuracy comparison.

**Code-grounded hypothesis:** In [`ft5955_native_action.c`](../driver/live-snapshot-2026-10-16/libfprint/drivers/ft5955_native_action.c), the worker starts and waits for its MOH subprocess `READY 1` **before starting the first** [`ft5955_native_scan()`](../driver/live-snapshot-2026-10-16/libfprint/drivers/ft5955_native_capture.c). The CLI's verification prompt need not indicate this worker has already armed status polling. The scan requires an observed OFF (`0x06`) followed by ON (`0x05`); if the first finger contact occurs before scanning begins, the code can start with ON while `armed=FALSE` and will ignore held contact until a later OFF→ON edge. Waiting after the CLI prompt plausibly makes the first valid edge easier to observe; repeated taps provide later edges after startup. An additional early-image/10-ms settling issue remains possible. These **explanations are hypotheses, not proof** without event timing / terminal status evidence.

**Next engineering step, without more enrolment or random delays:** add opt-in, no-biometric-content **monotonic-timestamp tracing** of (a) worker start, (b) successful MOH `READY`, (c) first observed OFF, (d) first observed ON, (e) image transfer completion, and (f) matcher outcome category (MATCH, NO_MATCH, RETRY QUALITY). Trace **timing/state only**, not pixels or templates, and preserve the current staged build and original immutable snapshot. First check whether prompt precedes scan arming. Only then choose an isolated fix, such as separating readiness/arming from capture or adjusting post-contact settling. **Do not remove the OFF→ON gate blindly**: it prevents accidental reuse of a held/stale frame.

The user's experimental trial currently appears **active (override installed)**, despite fprintd being idle when queried. The user-tested rollback is `bash "$HOME/Projects/ft5955-poll100-build/tools/ft5955_kde_trial.sh" --stop`. **No rollback has yet been reported for this later 100-ms trial**, so do not claim restored packaged libfprint until it runs and confirms success.

## 18 October — independent early-contact experiment prepared (NOT YET HARDWARE TESTED)

**Reason:** On the verified 100-ms libfprint driver the user reports about 80% first-press failures if pressing immediately after the verify message, about 30% if waiting an additional second, and about 95% success using fast tapping. The original worker waited for MOH `READY 1` before first querying the USB status (which requires observed OFF `06` → ON `05`). There is a plausible startup race, but no timestamp trace has yet proved the precise cause.

**Opt-in source experiment:** On branch `feature/ft5955-early-contact-parallel`, `verify_ft5955_clean_clone.py --stage --early-capture` reconstructs the same hash-pinned upstream libfprint from verified patches and then edits **only its disposable source**:

- Keeps **100-ms / 1,200-poll** bounded finger queries, same `0x82` status / `0x80` readiness / `0x81` capture commands, 10-ms settle delay and OFF→ON re-arm gate.
- On **verify**, starts the MOH gateway handshake in a **separate cancellable GThread** while the operation worker **immediately polls/captures the physical USB device**. The first image stays in the worker's private RAM; it is sent over the existing gateway protocol only after `READY 1` from MOH. All further re-try captures use existing path. The **enrol** sequence is untouched.
- Uses operation-scoped `GCancellable` on both I/O flows; failures and cancellation cancel/join gateway initialisation before cleaning the subprocess and wiping the worker's frame buffer. No new image persistence, templates, permission changes, PAM, USB commands or bypass of the MOH matcher.
- Stages separate library only at `~/.local/state/ft5955-system-trial/stage-earlycapture`; the known-good `stage` and 100-ms `stage-poll100` remain untouched. The existing guarded installer loads this only via `--start-earlycapture`; `--stop` remains unchanged.
- **CI source-transformation tests + wrapper syntax are passing.** This does **not** replace a real C compilation and sensor recognition test. Any first touch that occurs *before USB monitoring begins* may still require another OFF→ON; the fix isolates MOH startup from detection, but does not promise to accept a pre-held finger.

**User build preparation (safe, no system changes):**

```bash
BASE="$HOME/Projects/ft5955-independent-build-check"
NEW="$HOME/Projects/ft5955-earlycapture-build"
git -C "$BASE" fetch origin feature/ft5955-early-contact-parallel:refs/remotes/origin/feature/ft5955-early-contact-parallel &&
git -C "$BASE" worktree add --detach "$NEW" origin/feature/ft5955-early-contact-parallel &&
python3 "$NEW/tools/verify_ft5955_clean_clone.py" --stage --early-capture
```

Do not switch or reset the original checkout with local changes. **After** a successful build, if the 100-ms system trial is still installed, first `bash "$HOME/Projects/ft5955-poll100-build/tools/ft5955_kde_trial.sh" --stop`. Stop the packaged system `fprintd` service if it is active, then explicitly start the new short-lived experiment using `bash "$NEW/tools/ft5955_kde_trial.sh" --start-earlycapture`. Use `bash "$NEW/tools/ft5955_kde_trial.sh" --stop` to restore the original service. No re-enrolment and no PAM login configuration.

**Windows comparison remains intentionally outside this experiment:** Windows' native driver used status `0x80` selector `0x02` (seen `00→01→00`) and a companion GPIO `0x37`; our Linux capture uses `0x82 73 01` (`06/05`). These are different host queries to the sensor, but Windows and Linux are not concurrently polling it in our setup. Whether `0x37` affects sensor state, images or readiness remains unproven. Do **not** add these commands just to make this experiment pass.

## Completed alternatives to avoid revisiting

- An extra hardened `ft5955-engine-smoke.service` with a fake engine **passed** non-root socket/UID tests, but **nested bubblewrap inside that service failed** (`ERROR BWRAP_NAMESPACE_UNAVAILABLE`). Temporary units, socket and service account were removed. The team deliberately **stopped pursuing double sandboxing** and succeeded with the existing user-session MOH/bwrap route instead.
- USB Claim permissions in the earlier private test required a temporary ACL on the identified device node. The standard system service already had USB access; no separate physical unplug test is necessary.
- **GitHub housekeeping, 17 October:** [consolidation PR #4](https://github.com/Inforce855/focaltech-5955-linux/pull/4) was **merged into `main`** with full history; the fully represented earlier private-[`fprintd` PR #2](https://github.com/Inforce855/focaltech-5955-linux/pull/2) was **closed as superseded without deleting its branch**. The older [MOH engine research PR #1](https://github.com/Inforce855/focaltech-5955-linux/pull/1) stays **open** because it contains substantial additional `engine/` code and tests not yet reviewed for merging to `main`. **Do not delete those branches, run `git clean` in live trees, or rewrite the pinned snapshot.**

## Safe operational note

The **lab trial was fully rolled back**; no additional commands are needed to keep the normal system in its existing state. If a future trial is deliberately authorised, consult the actual [documented setup and stop scripts](kde-short-lived-trial-2026-10-17.md), check OS versions and exact rollback rather than assuming the environment has not changed. Never commit actual fingerprint data, vendor DLLs or sensitive logs.
