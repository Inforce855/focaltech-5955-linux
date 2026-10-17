# First real KDE enrol / verify experiment — SHORT-LIVED LAB TRIAL

**Updated 17 October 2026. LIVE Nobara system trial and KDE registration PASSED for both index fingers, as reported by user. Verification and fingerprint login are NOT yet proven; no PAM enabled.**

After the user's successful Timeshift snapshot, we chose to reuse the original functioning ordinary-user MOH + bubblewrap runner instead of attempting **nested bwrap inside an already sandboxed systemd service**, which failed with `ERROR BWRAP_NAMESPACE_UNAVAILABLE`. The completed non-root systemd socket mock and reversible system-driver discovery/rollback tests remain valid.

## What is changed for this experiment

- [Ordinary-user broker](../tools/ft5955_engine_broker.py) has opt-in `--serve --serve-user-trial`: creates a root-peer-only AF_UNIX socket at `/run/ft5955-engine/engine.sock` (mode `0600`, parent owned by invoking user mode `0700`). Accepts **only root UID peers** per SO_PEERCRED. It launches existing [`engine_gateway.py`](../driver/live-snapshot-2026-10-16/engine/engine_gateway.py) as the login user, using the existing `~/Projects/focaltech-5955-moh-test` code and pinned root-owned DLL; never as root. This deliberately remains **user-controlled**, therefore **UNSUITABLE for production/PAM authentication**.
- [Privileged activator/rollback](../tools/manage_ft5955_kde_trial.sh) reuses the already verified `manage_ft5955_system_trial.sh --activate` and the **already staged** identical driver library. Then copies only the root-side Python byte-stream relay into `/opt/ft5955-system-trial`, atomically replaces its single known trial drop-in with `FT5955_EXPERIMENTAL_ENABLE=1` and gateway path, reloads/restarts normal fprintd, and checks the exact mapped library and real `GetDevices`.
- [Normal-user single-command wrapper](../tools/ft5955_kde_trial.sh) orchestrates a private `/run` socket directory, ordinary-user broker launch, and root activation. `--stop` restores original normal-system fprintd **before** stopping the broker. Both scripts fail closed on unexpected pre-existing resources. No PAM/SDDM modifications and no arbitrary removal of other users' files. No systemd broker service and no new bubblewrap sandbox layer.

## How to try it on the one known supported machine

**Experimental biometric enrolment creates sensitive templates in normal fprintd storage; Timeshift may not cover all data, especially /home. The existing driver rollback does NOT remove saved fingerprints.** Before enabling a real fingerprint authentication mechanism, a separate matching-protocol authentication/template-integrity review is required. The `FT5955_ALLOW_UNVERIFIED_ATTACH` diagnostic build flag remains unsuitable for real login security.

Once the user chooses to attempt the normal-service KDE experiment:

```bash
REPO="$HOME/Projects/ft5955-independent-build-check"
git -C "$REPO" pull --ff-only &&
bash -n "$REPO/tools/ft5955_kde_trial.sh" &&
bash -n "$REPO/tools/manage_ft5955_kde_trial.sh" &&
bash "$REPO/tools/ft5955_kde_trial.sh" --start
```

If activation reports a real driver and device, try **KDE System Settings → Users → fingerprint enrollment**. KDE UI availability/version is not established; a standard `fprintd-enroll` client is a secondary test path. Enrolment/verification is unproven through this new bridge and may fail. Avoid exposing biometric raw data/templates, enabling PAM, or repeatedly enrolling.

Stop/rollback (whether or not KDE enrolment worked):

```bash
bash "$HOME/Projects/ft5955-independent-build-check/tools/ft5955_kde_trial.sh" --stop
```

If activation fails, the wrapper attempts automatic rollback, but its privileged code is newly written and has not yet been run on Nobara. Look carefully at the terminal for rollback warnings; don't assume a Timeshift snapshot replaces verifying recovery. Original staged driver SHA is preserved and the OS's original libfprint stays packaged under `/usr/lib64`.

## Observed real KDE results — user report, 17 October 2026

- User ran `git pull --ff-only && bash tools/ft5955_kde_trial.sh --start`, saw `PASS: packaged service unchanged; staged library verified` (SHA-256 `003ed7e6d53109ad355b653f3b5a9a6cfb33c99e150ae5e58ed7f6ff41fd7d4e`).
- Real `fprintd` PID **18010** mapped the experimental libfprint during initial reversible discovery activation, then real `fprintd` PID **18185** mapped the experimental library after enabling the **user-session** matching-engine broker. `GetDevices` returned `/net/reactivated/Fprint/Device/0`.
- KDE System Settings → Users visibly offered **Configure Fingerprint Authentication**. User subsequently reported: **“I just added my left & right index fingers!!”** Treat as **real KDE enrolment success for both fingers**, not as measured false-accept resistance, verified fingerprint recognition, successful PAM authentication or independent user-template attestation.
- **Verification PASS, user-reported:** standard `fprintd-verify` produced genuine `verify-match` results after KDE enrolment. User says **approximately 85% success with 3–4 distinct taps** (fresh lift/re-press on sensor); this is a practical informal estimate, **not** 85% first-press recognition, formal benchmark, negative-finger false-accept testing, or PAM login success. Previous finger-on/off studies established a new image needs fresh contact. The exact reason for misses remains undetermined. No need to enrol more fingers to mark end-to-end functionality achieved. Keep login/password unchanged. Roll back experimental system trial using `bash tools/ft5955_kde_trial.sh --stop` when finished; enrolled prints in fprintd storage are *not* removed automatically.

## Verified user-run rollback — 17 October 2026

Following real KDE enrolment of both index fingers and observed `fprintd-verify` matches, user ran:

```bash
bash "$HOME/Projects/ft5955-independent-build-check/tools/ft5955_kde_trial.sh" --stop
```

The terminal confirmed that the experimental biometric gateway was **disabled**, the user-session relay removed, the experimental systemd drop-in and separate library removed, and the **original packaged Nobara `libfprint` / `fprintd` retained**. Script printed `PASS: experimental driver removed; original Nobara fprintd restored` and `No PAM changes were made`. Standard D-Bus activation will load the packaged library; the original library's next **actual runtime mapping** was not independently verified after rollback. No Timeshift restore required. Stored test prints in `/var/lib/fprint` may remain and were **not** deleted by this script.

**Cycle PASS: installation → real KDE enrolment of two fingers → observed `verify-match` → successful rollback.** Production login/security readiness remains **NOT APPROVED**; `FT5955_ALLOW_UNVERIFIED_ATTACH`, user-controlled matching engine, template integrity, and inconsistent first-press recognition remain open.

## Validation scope

GitHub Actions passed shell syntax and ordinary-user synthetic Python broker transport [run 39026507585](https://github.com/Inforce855/focaltech-5955-linux/actions/runs/39026507585). CI never exercised actual MOH DLL, fingerprint enrolment, user-session root peer socket or live root service activation. **Those separate system steps now have first user-reported success for device integration and KDE enrolment** (as recorded above). CI scope remains synthetic; the user's real normal-service fingerprint verification now produced `verify-match` with inconsistent first-touch capture, but PAM login remains untested and intentionally disabled. This is still not a security-reviewed production login release.
