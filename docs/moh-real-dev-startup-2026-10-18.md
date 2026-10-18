# Real MOH startup in independent development service — 18 October 2026

The real Windows DLL **started successfully in standalone bubblewrap as UID 955**, with `DllMain=1`, engine `READY`, `DONE`, and exit 0. This is a hardware-host observation, **not** a systemd-service success or an authorisation result.

This experimental `ft5955_dev_real_startup_server.py` is designed for the existing **separate** `ft5955-engine-dev.socket` and cannot verify fingerprints: a root connection triggers a bounded, empty-stdin MOH startup and returns only `ERROR DEV_MOH_STARTED_NO_AUTH` or `ERROR DEV_MOH_START_FAILED_NO_AUTH`. Neither result can be a PAM success. It never reads fingerprint samples or templates.

**Do not replace the active dev mock service yet.** The existing hardened systemd service previously failed to create nested bubblewrap namespaces. The standalone UID 955 proof does **not** establish that this service configuration permits bwrap. This source is ready for review; an installer and rollback **must** be separately validated before switching the dev service. Do not disable `NoNewPrivileges`, `ProtectHome`, namespace restrictions, or the original MOH sandbox merely to make it start. Do not touch live `/run/ft5955-engine`, fprintd, PAM or password unlock.

The source uses the audited compiled ELF at `/opt/ft5955-dev/live-identify` and pinned vendor DLL path; the running synthetic mock remains the known-good -dev baseline. No production authentication is authorised.
