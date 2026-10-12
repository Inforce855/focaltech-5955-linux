# Working Windows VM as a reference: redacted Linux-host USB observation

**12 October 2026.** The owner has successfully authenticated by fingerprint in a Windows VM with the exact physical FocalTech **2808:5955** device passed through. This independently confirms a functioning Windows software stack and provides a controlled working reference; it does **not** establish how its private recognition algorithm works.

## Objective

Compare the Windows driver's USB command sequence with our already verified Linux sequence, **without capturing or sharing biometric image bytes**. Priority questions:

1. Does Windows query `0x80 selector 0x07`, setting device flag `+0x268`? Is the reply `0` (AES block decryption bypassed) or `1` (conditional AES-like path used)?
2. Does Windows send logical mode-control command `0x87` before image request `0x81`, or additional setup commands absent from our Linux sequence?
3. Does Windows request multiple `0x81` frames per fingerprint touch?

The original DLL call graph and image stages are documented in [Windows image conversion research](windows-moh-image-conversion-2026-10-12.md).

## First safe test (Linux HOST, Windows VM left intact)

This uses the Linux kernel `usbmon` text stream. It is **read-only**: no USB writes, resets, reconfiguration, device-driver patching or enrolment changes. The program does not store packet captures or fingerprint data. It displays only command numbers, size/counts, and one validated flag value from selector `0x07`; any large USB input transfer is redacted.

On **Nobara**, with the Windows VM running and the reader attached to it:

```bash
cd ~/Projects/focaltech-5955-linux
git pull --ff-only

.venv/bin/python -m unittest discover -s tests -p 'test_windows_vm_usbmon_probe.py' -v

lsusb -d 2808:5955
sudo modprobe usbmon
sudo .venv/bin/python tools/windows_vm_usbmon_probe.py --seconds 90
```

While it runs, **lock Windows and unlock it with one fingerprint press**. For this first test there is no need to install anything in Windows, redo enrolment, or unplug the reader. Paste **only** the script's already-redacted textual command summaries.

If `0x07 mode flag: NOT OBSERVED`, that is not a failure: Windows may perform this query only during device initialisation, which could have happened before the monitor started. For the next controlled test we can observe the start of Windows' device initialization, potentially by temporarily unassigning and reassigning this USB device using the VM manager. Do that only after checking the VM configuration; don't issue an unknown USB command manually.

**Note:** `lsusb` displays a USB bus/device address; USB address can change when the device is re-enumerated. The script automatically detects a unique `2808:5955`. If needed, pass `--bus N --device M` explicitly using the `lsusb` values. If `/sys/kernel/debug/usb/usbmon/0u` is unavailable, ensure debugfs is mounted and the usbmon module is loaded; investigate rather than changing kernel or guest configuration blindly.

## Data safety and boundaries

**A full USB packet capture during Windows Hello can contain a real 10,240-byte fingerprint image**, private biometric credentials or other device state. Never publish `.pcap`, `.pcapng`, raw USB hex dumps or full unredacted terminal logs from captures. The supplied monitor is intentionally narrow and doesn't print or save pixel data. Do not assume that an arbitrary external trace tool provides comparable privacy protection.

Windows sign-in confirmation is not proof the Windows-to-device transport contains an 8-bit fingerprint; USB still carries whatever the vendor protocol specifies, and the WinBio driver corrects its contents in memory.

For deeper analysis, we may use Wireshark/usbmon **locally** on the Linux host, but any full capture should stay local, be tightly time-bounded, and have its sensitive content removed before any transfer or commit. Official references: [Wireshark USB capture](https://wiki.wireshark.org/CaptureSetup/USB); [Windows guest + Linux usbmon procedure](https://github.com/liquidctl/liquidctl/blob/main/docs/developer/capturing-usb-traffic.md).
