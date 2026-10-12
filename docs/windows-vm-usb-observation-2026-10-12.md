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

## First real Windows Hello host trace — 12 October 2026

The owner authenticated successfully using the **Windows VM and the exact 2808:5955** sensor, while running the deliberately redacted Linux-host usbmon observer. All eight original synthetic observer tests passed on Nobara.

Observed, in the monitored interval (not necessarily Windows driver initialization):

| Logical command | Count | What was seen |
| --- | ---: | --- |
| `0x80`, selector `0x02` | 221 | repeated one-byte status queries |
| `0x37` | 222 | three-byte GPIO-related commands |
| `0x82` | 2 | around the single image request |
| `0x81` | 1 | one requested fingerprint image |
| image-sized IN transfer | 1 | **10,246 bytes**, full biometric payload suppressed |
| `0x87` | 0 | no mode-control request **in the observed portion** |
| `0x80`, selector `0x07` | 0 | optional AES image-mode flag still **unknown** |

**Event ordering around the successful capture:**
```text
(repeating 0x80 selector 0x02, then 0x37)
0x82 (2 parameter bytes, redacted)
0x81 (one fingerprint-image request)
IN 10246 bytes (image content redacted)
0x82 (2 parameter bytes, redacted)
(repeating 0x80 selector 0x02, then 0x37)
```

### What the exact matching Windows DLL tells us

Additional read-only disassembly of the original archived **MOH `FtWbioDriverUmdfV3.dll`** (hash in linked image-conversion report) reveals:

- At `0x180009C80`, the routine named **`ff_sc_query_finger_status`** (the literal function name is embedded at `0x18001B710`) calls `0x180007B8C` with selector `0x02` and one-byte return length: **logical `0x80` with payload `02 01`**. The result is compared to zero to produce the boolean return.
- The same routine then constructs **three bytes `01 01 01`** and calls the helper at `0x1800069B4`. That helper is labelled **`ff_sc_GPIOSet`** (literal embedded name at `0x18001B4C0`) and sends logical **`0x37`** via `0x180008004`. This GPIO command is sent along the normal successful status-query path; we have not proved what hardware output it drives.
- This is separate from our previous Linux **`0x82 73 01`** finger-status query. It cannot be assumed that these methods are equivalent or that `0x37` is a required image-quality correction.
- The redacted first monitor did not print the returned `0x80/0x02` status byte. The revised `tools/windows_vm_usbmon_probe.py` displays only **transitions** of that one-byte status (never image contents) and suppresses repeated status/GPIO lines.

**Interpretation:** Windows issues high-frequency status polling and a companion GPIO command. The fingerprint image size agrees with our Linux acquisition framing. We have **no direct evidence yet** that the Windows and Linux frames have identical contents, that `0x37` affects image calibration, or that AES decryption is enabled for the device. The image reconstruction algorithm remains incomplete.

### Next controlled observation

For normal use, simply pull the updated observer and run its synthetic tests before any further monitoring:

```bash
cd ~/Projects/focaltech-5955-linux
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_windows_vm_usbmon_probe.py' -v
```

The monitor will now show meaningful status transitions with much less output. To discover selector `0x07`, the monitor must be active **before the Windows driver initializes**; locking/unlocking a running Windows instance is unlikely to show startup-only queries. That future test may use a controlled Windows restart with the monitor already active, without changing Windows' driver or issuing any unverified sensor commands. USB device bus/address can change on re-enumeration, so treat a missing `0x07` as *not observed*, never as flag zero.

Neither original logs nor biometric images should be committed. Only the aggregate command observations above are retained.

## Second reference trace: full Windows VM restart + fingerprint login — 12 October 2026

**Direct observation, not inferred from static code:** The owner began redacted `usbmon` monitoring on Linux **before restarting the working Windows VM**. After the Windows guest restarted, they successfully authenticated using their fingerprint. The reported trace shows:

```text
0x82 (2 parameters, hidden)
0x37 (GPIOSet; repeated commands suppressed by monitor)
0x34 (handshake)
0x30 (0 parameters)
IN 51 bytes (data redacted; NOT known to be a fingerprint)
0x80 selector 0x05
0x80 selector 0x07
  validated single-byte response: 0x00
0x80 selector 0x03
0x80 selector 0x04
0x80 selector 0x01
0x80 selector 0x03
0x80 selector 0x04
0x80 selector 0x02 (repeated finger-status polling begins)
  validated finger-status byte: 0x00
0x82 (2 parameters, hidden)
0x82 (2 parameters, hidden)
  validated finger-status byte: 0x01
0x82 (2 parameters, hidden)
0x81 (fingerprint image requested)
IN 10246 bytes (image content REDACTED)
0x82 (2 parameters, hidden)
  validated finger-status byte: 0x00
```

The owner supplied event lines, **not the final full counts summary**, so no total counts are asserted for this second run.

### Conclusions that are now evidence-backed

1. **The physical unit, in this Windows initialization, reports selector `0x07` = `0x00`.** The MOH DLL branches on device-object offset `+0x268 == 1` before invoking its conditional AES-like raw-image transform. Therefore the observed initialization **bypasses that conditional decryption path**. This directly resolves the uncertainty recorded earlier in [MOH conversion research](windows-moh-image-conversion-2026-10-12.md). It does not exclude unrelated transformations elsewhere in the DLL.
2. **A successful Windows authentication used exactly one observed `0x81` and a 10,246-byte image-sized IN response.** This agrees with Linux's framed capture size; it does **not** prove the samples are bitwise identical, or that the conversion algorithms match.
3. The `0x80/0x02` status response transitions **`00 → 01 → 00`** across contact and release. These values are a different status interface from Linux's already observed `0x82 73 01` values `06` absent and `05` present; do not conflate them.
4. Windows initialization includes `0x34` and `0x30` (followed by 51-byte response), metadata selectors `05`, `07`, `03`, `04`, `01` and GPIO-related `0x37`. The redacted log does **not** reveal `0x82` payloads or exact meaning of `0x30`; no speculative USB operations are recommended.
5. **No `0x87` was displayed** in this observed sequence. This is not proof Windows never uses it in any other mode or setup.

### Updated engineering priority

Stop treating missing AES decryption as the leading cause of libfprint's zero-minutiae results for this hardware in the **observed mode**. The priority is now to reproduce and validate the ordinary, unencrypted conversion path `ff_sc_GetImage → 0x180005C78` with its already-disassembled spatial helper `0x180006184`, and then determine whether the vendor feature extractor, rather than NBIS, is required.

Do not commit Windows binaries, keys, fingerprint-image buffers, templates, or full usbmon dumps. Only command metadata and the non-biometric one-byte mode/status observations above are included here.
