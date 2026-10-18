# FT5955 dedicated MOH development service — verified 2026-10-18

## Demonstrated on host

The standalone MOH runner started under UID 955 and the independent systemd
socket-activated service returned `ERROR DEV_MOH_STARTED_NO_AUTH` after a
successful real Windows DLL startup. The latter response means **startup
succeeded**, not that biometric verification or authorization works.
Systemd service retained `NoNewPrivileges=yes`, `ProtectHome=yes`,
`ProtectSystem=strict`, `PrivateDevices=yes`, and an empty capability set.

Two specific bwrap errors were isolated:
1. `NETLINK_ROUTE socket: Address family not supported` required
   `RestrictAddressFamilies=AF_UNIX AF_NETLINK` in the dev unit.
2. `Can't mount proc on /proc: Operation not permitted` was resolved for
   the dev startup probe by replacing `--proc /proc` with a read-only
   bind of the host `/proc`. **That host proc exposure requires separate
   security review; a successful launch does not establish adequate isolation.**

## Avoid the mock-server regression

`systemd/ft5955-engine-dev.service` is intentionally the original MOCK
baseline used by initial staging and rollback. Installing it over the active
unit silently switches `ExecStart` back to the mock and produces
`ERROR DEV_ONLY_NO_AUTH`. **Do not treat the mock unit as the real unit.**

`systemd/ft5955-engine-dev-real.service` is the separately checked-in real
startup version. It specifies the exact real server ExecStart, retains
the same service/socket name and all other hardening, and explicitly allows
AF_NETLINK. This file is a *replacement candidate* for the installed
`ft5955-engine-dev.service`, not an additional service to enable alongside it.
Maintain the active unit backup and the existing mock rollback. A successful
response from the real service is `ERROR DEV_MOH_STARTED_NO_AUTH` only.

## Not yet implemented; do not confuse with completion

- No trusted transfer of real capture frames or templates from the driver to
  the **separate dev engine**.
- No real verification decision through that service; all responses deny auth.
- The working existing user-session MOH broker's matching is experimental,
  with unkeyed template integrity and decisions from user-controlled code.
- No proof yet that a compromised ordinary user cannot forge an authentication
  result or manipulate enrolment templates.
- No KDE/sudo PAM integration is approved. Password remains available.

## Definition of completion

1. Complete an authenticated, versioned request/reply interface between the
   driver-side trusted component and dedicated engine. Fail closed on errors,
   timeouts, wrong peers and protocol mismatches; never forward a user-owned
   `MATCH` claim as a privileged authorization.
2. Move template storage and integrity verification behind the trust boundary.
   Review enrollment, identity selection, replay resistance and the vendor
   Windows DLL / `UNVERIFIED_ATTACH` limitations.
3. Prove positive and negative *real hardware* verification through the
   independent service without PAM.
4. Only then assess KDE-only PAM using the existing backups and explicit
   rollback; do not change shared authselect/system-auth to reach KDE unlock.
5. Consider sudo separately after KDE's negative cases and recovery are tested.

This document preserves the already-working code and distinguishes **MOH
startup success** from **secure login completion**.
