# FocalTech 5955 Linux

Reverse-engineering and Linux userspace support for the **FocalTech USB fingerprint reader, VID:PID `2808:5955`**.

**Project status: exploration. No functional fingerprint driver yet.** The device is visible on Linux but was not recognised by `libfprint 1.94.100` and `fprintd 1.94.5` on Nobara (Fedora 44 base).

## Identified hardware

| Property | Observed value |
| --- | --- |
| Vendor / product ID | `2808:5955` |
| USB device revision (`bcdDevice`) | `20.03` (not necessarily the firmware version) |
| USB speed | 12 Mbit/s (full speed) |
| Interface | 0: CDC Data (`0x0a`) |
| Bulk IN endpoint | `0x82` (EP 2), max packet size 64 bytes |
| Bulk OUT endpoint | `0x01` (EP 1), max packet size 64 bytes |
| Linux kernel driver | None on interface 0 |
| Matching Windows driver | FocalTech MOH 5.10.66.6611, WinUSB / UMDF |

See [hardware notes](docs/hardware.md) and [roadmap](docs/roadmap.md).

## First diagnostic: USB probe

The initial probe is intentionally restricted: **it does not send fingerprint commands, bulk OUT transfers, vendor control requests, enrol fingerprints, flash firmware or change KDE/PAM authentication**.

On Nobara:

```bash
git clone https://github.com/Inforce855/focaltech-5955-linux.git
cd focaltech-5955-linux
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/usb_probe.py
```

The default mode only displays USB identity, interface and endpoint descriptors. It normally does not need root privileges.

To **optionally listen for unsolicited data**, for 15 seconds while touching and releasing the sensor:

```bash
sudo .venv/bin/python tools/usb_probe.py --listen --seconds 15
```

Listening claims interface 0 temporarily and performs **IN-only bulk reads** on endpoint `0x82`; there is no application data sent to endpoint `0x01`. It will refuse to detach an existing kernel driver. **No data is expected from many sensors until their protocol initialisation sequence has been sent**, so receiving no packets is a normal first result.

If root access is undesirable, we can later add a tightly scoped udev rule. Do not use generic world-writable USB permissions.

**Privacy:** Never commit or publicly post fingerprint images/templates, live USB captures, personal identifiers or logs containing biometric data. Review any reported packet bytes before sharing.

## Experimental live firmware-information query

**This is the first real USB command experiment. It has NOT yet succeeded on a physical sensor.** The candidate command was reconstructed from the manufacturer's Windows MOH DLL, not recorded from a working sensor. Although it appears to request information, its effect cannot be guaranteed before a successful test.

```bash
# Inspect the request without contacting the sensor:
.venv/bin/python tools/firmware_probe.py

# Only if you accept the experimental hardware risk:
sudo .venv/bin/python tools/firmware_probe.py --send
```

The live mode requires typing **SEND** before any bulk OUT transfer. It refuses a mismatched USB device revision or endpoint configuration, never detaches a kernel driver, sends **exactly one** five-byte request to endpoint `0x01`, and reads at most two times from `0x82` with bounded timeouts. There are no command retries, firmware writes, resets, authentication changes or enrolment procedures.

A timeout is a useful result: the sensor may require an initialisation sequence, and repeatedly sending the same request would not help. A USB reply is only an initial communication milestone; it is not fingerprint support. Review any raw data before posting publicly.

## Safety and scope

- Aim: an independently implemented Linux userspace driver, preferably integrated into `libfprint` / `fprintd`.
- Verify protocol before transmitting anything to the reader.
- Keep the proprietary Windows driver archive and binaries **outside this public repository**.
- Avoid firmware flashing and any PAM, KDE or system-library changes while prototyping.
- No compatibility claim is made for other FocalTech product IDs.

## Contributions

Hardware reports and independently developed protocol notes are welcome. Do not redistribute proprietary binaries or biometric samples.

No project licence has been chosen yet; substantial code contributions should wait until a licence is agreed.
