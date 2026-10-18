# MOH independent development service — 18 October 2026

This branch contains a **source-only** development service. It has **not** been installed or hardware-tested. It is not yet the real MOH engine.

## Isolation from the working fingerprint trial

- Dev socket: `/run/ft5955-engine-dev/engine.sock`.
- Dev code proposal: `/opt/ft5955-dev/ft5955_dev_mock_server.py`.
- Dev unit names: `ft5955-engine-dev.socket` and `ft5955-engine-dev.service`.
- Intended non-login account: `ft5955-engine` (not yet provisioned).
- It never references or removes the existing `/run/ft5955-engine` socket, or alters the fprintd override, libfprint, PAM, SDDM or enrolments.
- This mock does **not** launch the Windows DLL or claim to match fingers. For an authorised root peer it replies only `ERROR DEV_ONLY_NO_AUTH`; other UIDs receive no authentication response. This is intentional fail-closed groundwork, not a proof of MOH operation.
- The existing system service hardening profile and previous unsuccessful nested bwrap test remain documented. No double-bwrap attempt is planned.

## Required gates before deployment

1. Offline tests of the synthetic server's root-peer refusal and absence of `MATCH` or biometric content.
2. Documented, explicit installer/rollback **for only these -dev units**; independent of the live trial, without touching the live socket or service. Backup/rollback of any account or directory changes.
3. Prove isolated mock service reaches real systemd socket as a dedicated non-login account, without weakening protections. Preserve an independent shell session and existing password authentication.
4. Only then develop deployment of audited proprietary MOH code and protected enrolled template storage; re-review required sandbox and ABI restrictions. The current user-session matcher is still not safe for PAM.
5. PAM and KDE unlock remain **disabled** in this development stage.

Do not install these files manually as an authentication solution; installing the service alone does not create the service account, populate /opt or prove runtime functionality.
