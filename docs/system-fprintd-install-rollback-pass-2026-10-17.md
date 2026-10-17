# FT5955 staged Nobara system fprintd trial — activation AND rollback PASS

**Date:** 17 October 2026 · **Environment:** Nobara 44, system `fprintd 1.94.5-5.fc44`, packaged `libfprint 1.94.100-1.fc44` · **Status:** successfully activated for device discovery, then rolled back. **There is no active system-trial installation after this report.**

## Evidence from actual user-run terminal commands

The user updated the existing separate GitHub checkout and ran:

```bash
REPO="$HOME/Projects/ft5955-independent-build-check"
git -C "$REPO" pull --ff-only
bash -n "$REPO/tools/manage_ft5955_system_trial.sh"
python3 "$REPO/tools/verify_ft5955_clean_clone.py" --stage
```

The stage build independently fetched the pinned libfprint release, verified the archived source and all three reviewed patches, and compiled **109/109 Ninja steps** for only `focaltech_5955` (27 Meson targets). It created a user-owned staging directory `~/.local/state/ft5955-system-trial/stage` containing the rebuilt library and checksum. **Observed staged SHA-256:**

```text
003ed7e6d53109ad355b653f3b5a9a6cfb33c99e150ae5e58ed7f6ff41fd7d4e
```

The user then ran:

```bash
sudo bash "$REPO/tools/manage_ft5955_system_trial.sh" --activate
```

Output reported that original system `fprintd` service configuration was unchanged before installation, and the staged library checksum matched. The installer copied it into root-owned `/opt/ft5955-system-trial/lib/` and temporarily created **only** the dedicated `/etc/systemd/system/fprintd.service.d/90-ft5955-system-trial.conf` service override. It explicitly kept `FT5955_EXPERIMENTAL_ENABLE=0` and did not provide a MOH gateway. It started normal system `fprintd` and confirmed from `/proc/PID/maps` that **PID 11201 was running the exact staged experimental shared library**:

```text
PASS: packaged service unchanged; staged library verified (003ed7e6d53109ad355b653f3b5a9a6cfb33c99e150ae5e58ed7f6ff41fd7d4e)
PASS: system fprintd PID 11201 mapped exact root-owned experimental .so
SYSTEM GETDEVICES: ([objectpath '/net/reactivated/Fprint/Device/0'],)
PASS: system-service FT5955 discovery trial active (no biometric operations).
Password login and Nobara RPM-owned libfprint remain unchanged.
```

**Result: system-service library activation and normal system-D-Bus device discovery PASS.** This is stronger than the earlier private-bus tests: the ordinary installed `fprintd` process really loaded the FocalTech driver.

The user **immediately executed the explicit rollback**:

```bash
sudo bash "$REPO/tools/manage_ft5955_system_trial.sh" --rollback
```

Its output:

```text
Stopping ONLY fprintd.service, then restoring packaged runtime...
PASS: trial service override and separate binary removed.
PASS: original RPM-owned libfprint and fprintd untouched; packaged service restored.
Normal D-Bus activation will next load original system libfprint.
```

**Result: rollback PASS as reported by the installer.** The dedicated service override and the temporary `/opt` library were removed; systemd configuration reloaded and system `fprintd` stopped. The standard packaged binary remained untouched. The original library was **not independently reloaded/tested after rollback** in the submitted log, so treat that as a sensible optional read-only follow-up, not as demonstrated runtime proof.

The staged **user-owned** library remains in `~/.local/state/ft5955-system-trial/stage` unless deliberately removed separately. Root rollback does **not** delete that staging artifact. This is intentional and not an active installation.

## Limits and next safe milestone

- **No system biometric operation tested.** The normal service's `GetDevices` succeeded, but the user has **not** run a system-level `Claim`/`Release` in this trial, nor any normal-service enrol/verify. Previous private-DBus Claim/Release and private MOH matching tests remain separate.
- **No fingerprint authentication enabled**, no PAM/config changes and no stored templates. `fprintd-pam` was absent in preflight; the password login path remains available.
- A normal hardened systemd `fprintd` service may not support running the experimental Windows MOH bridge at all: `ProtectHome=yes`, `ProtectSystem=strict`, `NoNewPrivileges=yes`, `MemoryDenyWriteExecute=yes`, etc. The Windows MOH dependency remains; native matching is the eventual goal.
- **No repeat 12-impression enrolment or physical unplug test needed.** Previously recorded rejection/retry/cancel/reopen tests must not be silently marked unfinished again.

**Next action:** before an ongoing installation or KDE GUI enrolment, review how to implement safe non-root MOH execution and stored-template protections (or native matcher path). A **separate optional system-level Claim/Release-only** check is possible using the already successful reversible installer, without touching biometrics. Keep the rollback verified and preserve the original OS login mechanism.
