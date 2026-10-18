# FT5955 dedicated MOH development service — verified 2026-10-18

## Update — real dedicated-service hardware verification PASS, 18 October 2026

**Hardware-host result reported by user:** the guarded `run_ft5955_dev_hardware_trial.sh --start`
completed the 21-C-file protocol engine build, root-owned staging, socket-based
`READY 1 → BYE` smoke test and switch of the existing *experimental* system
`fprintd` gateway to the UID955 MOH development service. The installed
`ft5955-engine-dev-protocol.service` runs the real protocol gateway inside
the hardened dedicated account, not the prior startup-only probe.

The subsequent actual `fprintd-verify` enumerated both saved fingers. The
first user-run right-index attempt returned `verify-no-match`; **this is
expected to occur on some contacts** because the reader's location makes
finger positioning difficult, especially on the right hand. **A new
`fprintd-verify -f left-index-finger` run returned `verify-match (done)`
on the first attempt**, confirming an actual successful biometric decision
end-to-end through the independent MOH service.

This supersedes the earlier below statement saying no verification exchange
exists through the separate engine; that paragraph is retained as a dated
pre-integration description. **No new enrolment was required.**

**Current host state:** the independent dev hardware trial has been started;
there is no reported rollback after this successful verification. Its
activation explicitly left PAM, KDE password unlock, SDDM, sudo and authselect
unchanged. Roll back this trial with:
`sudo bash /opt/ft5955-dev/run_ft5955_dev_hardware_trial.sh --stop`.

**Not production-approved:** a successful match does not fix the unkeyed
libfprint template envelope, ownership/identity binding of saved templates,
the proprietary runner's `FT5955_ALLOW_UNVERIFIED_ATTACH`, and the dev
sandbox's read-only host `/proc` exposure. The raw template still passes
through `MODE V` from fprintd; verification of stored-template authenticity,
user-account separation, negative cases and cancellation remains to be done.
**Do not enable KDE PAM or sudo yet.** This completes the real-hardware
matching milestone, not secure-login approval.

---

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
