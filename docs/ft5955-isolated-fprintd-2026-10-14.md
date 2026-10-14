# FT5955 — isolated fprintd 1.94.5 initial discovery trial (14 October 2026)

## Environment

- Nobara 44: `fprintd-1.94.5-5.fc44.x86_64`, `libfprint-1.94.100-1.fc44.x86_64`.
- Stock executable: `/usr/libexec/fprintd`, dynamically linked to `libfprint-2.so.2`; no RPATH/RUNPATH.
- Private experimental libfprint from `~/Projects/libfprint-ft5955/build-ft5955/libfprint` successfully selected by setting `LD_LIBRARY_PATH` for a test process; system libfprint left alone.
- `dbus-run-session`, `dbus-daemon`, `bwrap` available.
- Original `/etc/fprintd.conf` specifies `[storage] type=file`; binary contains `STATE_DIRECTORY`, `/var/lib/fprint` strings. Actual temporary-store write behaviour **not yet exercised**.
- The normal `fprintd.service` was inactive before the test; no installed service unit, PAM configuration, system package or login setting was edited.

## Actual first isolated test

The operator launched `/usr/libexec/fprintd` as an unprivileged user inside `dbus-run-session`, exported `DBUS_SYSTEM_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS` so that the daemon's **system bus connection** was redirected to a private bus, pointed `LD_LIBRARY_PATH` at the private driver, and set `STATE_DIRECTORY` to a `mktemp -d` path with shell EXIT cleanup. The FT5955 experimental feature flag and original MOH engine gateway path were set; no enrolment/verification was requested.

Private bus call:

```sh
gdbus call --address "$DBUS_SYSTEM_BUS_ADDRESS" \
  --dest net.reactivated.Fprint \
  --object-path /net/reactivated/Fprint/Manager \
  --method net.reactivated.Fprint.Manager.GetDevices
```

**Observed successful response**:

```text
([objectpath '/net/reactivated/Fprint/Device/0'],)
```

**PASS: device object exported by isolated fprintd through private libfprint.** No device property, Claim, Open, enrolment, on-disk print store or login operation is confirmed yet. Device identity should be independently checked by reading `org.freedesktop.DBus.Properties.GetAll` on `/net/reactivated/Fprint/Device/0` with interface `net.reactivated.Fprint.Device`; current result alone establishes device enumeration, not a full functional login path.

Daemon logged two **nonfatal, expected** warnings:

- `Failed to disable USB persist ... /sys/bus/usb/devices/3-4/power/persist`, familiar warning from previous native driver tests.
- `Failed to install a sleep delay inhibitor: ... org.freedesktop.login1 ... ServiceUnknown`, because the private D-Bus has no logind service.

## Next safe step

Read D-Bus device properties `name`, `scan-type`, `num-enroll-stages`, `finger-present`, and `finger-needed` on the same disposable private bus. Upstream fprintd 1.94.5 documents these properties; `num-enroll-stages` may be `-1` before the device is claimed.

Before private-bus enrolment, independently confirm file storage path selection and PolicyKit authorisation design; normal fprintd Claim and Enroll methods use PolicyKit on the system bus. Do not expose the experimental daemon on the user's real system bus, change installed units, write to `/var/lib/fprint`, or enable PAM yet.


## Live D-Bus GetAll property check — 14 October 2026

The operator repeated the isolated private-bus `fprintd` run with the private FT5955-enabled libfprint and queried `org.freedesktop.DBus.Properties.GetAll('net.reactivated.Fprint.Device')` on `/net/reactivated/Fprint/Device/0`. **Success**:

```text
({'name': <'FocalTech 5955 (experimental)'>, 'num-enroll-stages': <12>, 'scan-type': <'press'>, 'finger-present': <false>, 'finger-needed': <false>},)
```

This establishes successful propagation of the driver name, 12-stage enrolment count, press-type sensor and idle finger-state properties through stock fprintd over the private bus. It does not exercise Claim, authorisation, enrolment, or verification.

Upstream fprintd 1.94.5 `src/file_storage.c` `get_storage_path()` selects the `STATE_DIRECTORY` environment variable if present/nonempty, falling back to `/var/lib/fprint` otherwise. Enrolment writes a serialised `FpPrint` to the computed per-user/per-driver/per-device file path. Therefore never omit `STATE_DIRECTORY` in live private-bus enrolment experiments; continue with a dedicated temporary path. Upstream `device.c` runs PolicyKit authorisation for claimed and enrol/verify methods; a private D-Bus service without a PolicyKit authority may fail such requests. No privilege or system configuration changes are warranted solely to bypass the failure.
