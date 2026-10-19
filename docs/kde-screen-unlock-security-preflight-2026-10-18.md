# KDE screen-unlock authentication — security preflight (18 October 2026)

**State: read-only planning and diagnostics only. Not authorised for live PAM activation.**

## Installed systemd/socket review — 19 October 2026

User showed full `systemctl cat ft5955-engine-dev.service ft5955-engine-dev.socket` output and `namei -l` of live paths. Findings:
- Effective `/etc/systemd/system/ft5955-engine-dev.service` runs `/usr/bin/python3 -I -B /opt/ft5955-dev/ft5955_dev_protocol_server.py` with `User=ft5955-engine`, `Group=ft5955-engine`, and depends on `ft5955-engine-dev.socket`. Configuration includes `NoNewPrivileges`, `ProtectHome`, `ProtectSystem=strict`, `PrivateDevices`, `RestrictAddressFamilies=AF_UNIX AF_NETLINK`, `IPAddressDeny=any`, empty capability/ambient sets, and additional hardening options. Systemd's distribution-wide `10-timeout-abort.conf` adds `TimeoutStopFailureMode=abort`; do not mistake this for an FT5955 override.
- The socket listens at `/run/ft5955-engine-dev/engine.sock`, `SocketUser=ft5955-engine`, `SocketGroup=root`, `SocketMode=0660`, `DirectoryMode=0755`; actual socket `srw-rw---- ft5955-engine root` under `root:root 0755` parent. Access controls are consistent with the intended root fprintd client and separate engine account. The checked-in broker's `SO_PEERCRED` handling explicitly allows only peer UID 0 in the active, non-test mode.
- The protected `/opt/ft5955-dev` directory is `root:root 0755`, with the server and template gateway Python modules `root:root 0644`. The vendor DLL's directory and file are root-owned and not writable by ordinary users; world readability of the DLL alone does **not** imply they can modify it. The protected launcher in GitHub checks root ownership and SHA-256 pin of the installed DLL.
- Thus these results reveal **no obvious unprivileged socket/file overwrite path**. This is not a complete proof of safe authentication. Root-only stored template directories coexist with an **unkeyed fingerprint-template digest**; account/credential binding, the installed fprintd gateway/library load path, vendor `UNVERIFIED_ATTACH` and read-only host `/proc` sandbox exposure still require attention before allowing broad PAM authentication.
- User has explicitly requested that the `-dev` unit/path be retired in the final maintained installation, **after** preserving and migrating the working implementation. Do not rename the active service yet.

**Immediate next check (read only):** examine the effective fprintd service `Environment` and loaded libfprint trial library/relay permissions to close source/runtime discrepancy. No systemd, PAM, module, or scanner changes at this step.

## Follow-up evidence — 19 October 2026 (supersedes parts of the 18 October baseline)

This dated handoff originally described the earlier **user-session** broker. The host subsequently demonstrated a separate **UID955 MOH service** using `ft5955_dev_protocol_server.py`, `ft5955_engine_broker.py` and `ft5955_dev_template_launcher.py`. The connection's root UID is checked with `SO_PEERCRED`; service/broker/launcher source restricts execution to the dedicated account or root-owned relay, and the launcher checks a pinned DLL digest. User reported that the socket now starts after reboot and that seven sequential left-index verification operations matched after re-enrolment.

User's **read-only** permissions check showed:
- `/var/lib/fprint` and nested user/driver directories owned `root:root` with mode `0700`. The fingerprint files are mode `0644` but are not traversable through these parent directories by ordinary users; do not claim that file mode alone exposes them.
- `/opt/ft5955-dev` owned by root; broker and protocol server Python files `root:root`, mode `0644`; `live-template` `root:ft5955-engine`, mode `0550`.
- `fprintd-pam` is now installed, superseding the previous missing-package statement.
- `authselect` profile `local` (features `with-silent-lastlog`, `with-mdns4`) passes `authselect check`, with `with-fingerprint` not enabled. `fingerprint-auth` still contains `pam_debug.so auth=authinfo_unavail`; `system-auth` has password rules and no `pam_fprintd.so`; KDE setting `Authenticators/Fingerprint` reads `false`. `polkit-1` includes `system-auth`.

**Revised assessment:** The old claim that a normal login user owns the currently used matching service is superseded by the protected UID955 architecture and the above permissions evidence. However the installed paths, effective socket peer restrictions and unit sandbox policy still need a read-only consistency check. Source code has no cryptographic MAC on the fingerprint template envelope; root-only storage materially limits ordinary-user template editing but does not by itself prove account separation, absence of protocol mistakes, anti-spoofing or safety of the vendor `FT5955_ALLOW_UNVERIFIED_ATTACH` path. The vendor sandbox's read-only host `/proc` bind also remains a declared concern.

**User-approved functional target:** enable **global** `authselect with-fingerprint` for password-alternative authentication, including KDE lock screen, Polkit authorisation and subsequently `sudo` as appropriate, keeping password fallback. Do not misstate this as a KDE-only goal. Activation still requires a trustworthy authentication path and tested recovery plan; no PAM changes were made during this review.

**Next:** inspect effective installed `systemd` service and socket units and pathname permissions (read-only), then address any *specific* gap before a guarded `authselect` update. Do not repeat fingerprint enrolment, matching baselines or timing experiments. Once operational authentication and security gates pass, migrate from the `-dev` service/path names to a maintained installation with tested rollback.

---

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
