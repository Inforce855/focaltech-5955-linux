# KDE screen-unlock authentication — security preflight (18 October 2026)

**State: read-only planning and diagnostics only. Not authorised for live PAM activation.**

## User-verified Nobara 44 baseline

- `kscreenlocker-6.7.5-1.fc44.x86_64`, `fprintd-1.94.5-5.fc44.x86_64`; `fprintd-pam` not installed. `authselect-1.7.1-1.fc44`, local profile with `with-silent-lastlog` and `with-mdns4`, with `authselect check` passing.
- `/etc/pam.d/kde` uses `password-auth`; `/etc/pam.d/kde-fingerprint` references `fingerprint-auth`. Current generated `fingerprint-auth` contains `auth required pam_debug.so auth=authinfo_unavail`, **not** `pam_fprintd.so`.
- `authselect test local with-silent-lastlog with-mdns4 with-fingerprint` showed that enabling the feature also inserts `auth sufficient pam_fprintd.so` in **`system-auth`**. Therefore **do not globally enable** `with-fingerprint` for the KDE-only experiment.
- `kreadconfig6 --file kscreenlockerrc --group Authenticators --key Fingerprint --default false` returned `false`; no explicit `[Authenticators]` section was seen. Do not assume this diagnostic alone confirms KDE's runtime support or the correct enabling mechanism; inspect actual locker source/runtime before changing settings.
- The user created and opened in Ark a local archive `/home/tim/PAM-Backup-18-10-2026_12-24-06.tar.gz`; `gzip -t` passed and the archive listing includes `etc/pam.d/kde`, `kde-fingerprint`, `system-auth`, `fingerprint-auth`, `etc/authselect/authselect.conf`. Archive restore has **not** been tested. Archive stays local, **never commit to GitHub**.
- Fingerprint registration, KDE enrolment and system `fprintd-verify` already work in the short-lived **lab** bridge. Do not repeat those tests merely to establish PAM availability. Password unlock remains working.

## Critical blocker: laboratory broker is not a trusted authenticator

- The current `tools/ft5955_kde_trial.sh` **deliberately refuses** to activate if `fprintd-pam` is installed; it says: `STOP: fingerprint PAM package present; trial is not safe for login.` Do **not** remove this guard to make an experiment run.
- Root system fprintd currently connects through a root relay to a MOH engine controlled by the login user. File/socket permissions against other users do **not** prevent the account owner from forging a match, swapping their engine or interfering with templates. Successful biometric recognition is not sufficient proof for PAM.
- Current template checksums are unkeyed SHA-256, not authentication/integrity against an account-controlled adversary. The MOH runner includes `FT5955_ALLOW_UNVERIFIED_ATTACH`. No hardware security/anti-spoof properties have been validated. Avoid false claims of production security.
- Previous hardened-service synthetic socket test PASSED, but **nested bwrap failed** and was deliberately abandoned. Do not revisit that experiment by default.

## Target boundary and acceptance gates

1. **Preserve the working driver and its immutable source/patch chain.** Prototype a privileged, service-owned matcher decision path **separate from the login user**, with protected match code, stored templates and configuration. Preserve isolation of proprietary Windows code; running unverified vendor code as root is not acceptable.
2. Ensure account-owned processes cannot issue `MATCH` decisions or alter trusted templates. Test negative cases by simulating tampered template, disconnected backend, wrong peer UID, altered helper executable, timeouts and rejected fingerprints. Every failure must fail closed.
3. Once a trustworthy service boundary and its tests pass, verify on the actual Nobara host that KDE locker invokes `kde-fingerprint`. Prepare **KDE-only** PAM activation using `pam_fprintd.so`, rather than switching shared `system-auth` globally. Installing `fprintd-pam` requires first changing the *lab-only* package guard safely through a **separate** production-ready installation path; it is not a safe immediate step.
4. Before locking: independently test **password unlock**, confirm rollback instructions from a second session or USB recovery, and verify a PAM fingerprint attempt does not disable password fallback. Never touch SDDM/auto-login/sudo during the KDE-only trial.
5. Test genuine finger, wrong finger, cancellation, timeout, broker outage, password fallback. Archive security observations but **never biometric data or secrets**.

## Current action

Run `bash tools/ft5955_kde_auth_preflight.sh` from a checkout of this branch to gather **read-only** current system state. It intentionally prints **NOT APPROVED FOR PAM** even if every operating-system configuration check is fine. No PAM edit, package installation, screen locking or service restart is performed.

**Repository scope:** Existing authoritative repository only: `Inforce855/focaltech-5955-linux`. Leave dirty checkouts untouched; fetch the new branch in a clean pre-existing Git worktree if preferred.
