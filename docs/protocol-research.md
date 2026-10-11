# Protocol research notes — FocalTech 2808:5955

Updated: 11 October 2026. This page distinguishes **verified observations**, **offline reverse-engineering findings**, and **unverified hypotheses**.

## Confirmed Linux hardware tests

- Device `2808:5955` enumerates at full-speed (12 Mbit/s), USB device revision `20.03`.
- Interface 0 is CDC Data (class `0x0A`), not bound to a kernel driver.
- Two bulk endpoints: OUT `0x01`, IN `0x82`; both have 64-byte USB maximum packet sizes.
- `fprintd-list "$USER"` on Nobara with `libfprint 1.94.100` returned `No devices available`.
- On **11 October 2026**, the standalone `usb_probe.py --listen --seconds 15` ran successfully, starting 11:39:25 BST and ending 11:39:40 BST. A user touched and released the reader during the interval.
- The listener received **zero non-empty USB IN packets**. This only shows that no unsolicited data were delivered while the interface was claimed for this brief test. It does **not** establish failure of the device or prove any particular start-up requirement.
- No application commands were sent, and firmware / authentication settings were unchanged.

## Offline Windows DLL inspection (source: user-owned MOH driver package)

File: `FtWbioDriverUmdfV3.dll` (x86-64 PE DLL), MOH package version `5.10.66.6611`.

String references include:

- `D:\\work\\Sensor\\FT9366\\newarch\\`
- `ff_sc_ReadData`, `ff_sc_WriteData`
- `ff_sc_CalcBCC`
- `ff_sc_GetSCFirmwareVersion`, `ff_sc_ReadFingerStatus`
- `ff_sc_local_DownloadSCFirmware`

Strings and development paths are *leads*, not proofs of chip or live wire protocol.

### BCC routine: confirmed calculation

Static inspection of the PE disassembly shows a function at image RVA `0x658C` (VA `0x18000658C` at preferred image base) which references the diagnostic string `ff_sc_CalcBCC`. Its active calculation loops over a pointer and 16-bit length, XORing successive input bytes into an initially zero accumulator, then returns the one-byte XOR.

The outgoing frame and live firmware-information response subsequently confirmed that the relevant frame BCC XORs the two length bytes, the command/response-type byte and all payload bytes. See [frame format and live capture](usb-frame-format.md).

## Firmware-version request path: partially recovered from static disassembly

The MOH `FtWbioDriverUmdfV3.dll` firmware-version function appears to begin at preferred-image VA `0x180006FD8`. The DLL is PE32+ x86-64, preferred image base `0x180000000`. In the routine:

1. At `0x18000702C`, it loads **`0x30`** into `CL` and calls helper `0x180008004` with no payload pointer and a zero length argument. This is a strong **candidate logical firmware-info request selector**.
2. Following a successful helper result, at `0x1800070C0` it sets `EDX=0x3F` and invokes a second helper at `0x180007760` with a destination buffer and an output-length pointer.
3. The response is treated as a bounded, NUL-terminated string and logged using `[Driver] I fw info: %s`.
4. The routine later examines the string for `APP`, and, if found, calls another shared helper (`0x180007B8C`) with arguments `0x05` and `0x02`, after which it logs a `version.chipid` value. These may be logical subcommands, not literal USB bytes.

**Updated after hardware success:** following additional analysis of the USB writer, the command's full on-wire representation was reconstructed as `02 00 01 30 31` and successfully sent from Nobara on 11 October 2026.

The next task is to trace the object's implementation of those send/read methods, or compare a genuine WinUSB trace of the request and response. No protocol-write capability is being enabled in the current probe.

## Hardware and offline test results — 11 October 2026

On Nobara, the initial descriptor probe identified `2808:5955` and its bulk endpoints. A 15-second bulk-IN listen received zero unsolicited packets. The user then ran `tools/protocol_codec.py` and `python -m unittest discover -s tests -v` successfully: the offline firmware-info encoder produced `02 00 01 30 31`, and **all seven synthetic tests passed**.

This validates the implementation against our current static protocol model, **not** the hardware.

### Additional setup-path observation

A further look at the MOH DLL disassembly shows that the routine at preferred-image VA `0x180008B80` calls several different helpers in sequence, including `0x180008780`, `0x180008328`, and `0x1800080C0`. The latter receives different one-byte arguments in the setup path. The exact effect of these calls is **not yet verified**, and we cannot currently establish which are mandatory before a firmware-information request.

The firmware-information command succeeded on the live reader **without** the separate setup path. Other fingerprint operations may still need configuration or wake-up commands. Do not transmit unverified configuration commands.

## First successful live firmware-information exchange — 11 October 2026

The user ran `sudo .venv/bin/python tools/firmware_probe.py --send`, explicitly confirming the single hardware transfer.

- USB OUT endpoint `0x01`: **5/5 bytes** transmitted: `02 00 01 30 31`.
- USB IN endpoint `0x82`: **51 bytes** received.
- Wire header `02 00 2e 04` declares **46 bytes** of response type and payload.
- Decoded firmware information: **`FT936x_APP_FW3032_USB_DEC_SV0.5_5849_PowerKey`**.
- The next byte, **`51`**, is the correct XOR BCC of bytes 1 through 48. It is **not** a `Q` in the firmware string.
- A final **`00`** appeared *after* the completed 50-byte framed response. Its exact purpose is unknown; the codec now tolerates **only one** such suffix.
- The initial codec rejected the 51-byte USB transfer because it expected exactly 50 bytes. This was a framing/parsing problem, **not** a failed USB transaction.

The returned identifier is a firmware build string, not proof of the physical sensor's exact silicon or firmware update history. The live communication milestone is verified; **finger detection, imaging, matching and `fprintd` integration remain unimplemented**.

The real captured response is now checked in the offline regression tests; users do **not** need to repeat the live USB command to validate the corrected decoder.

## Related project: research only, not a compatible driver

The project [inevitableDivu/focaltech-2808-6658-driver](https://github.com/inevitableDivu/focaltech-2808-6658-driver) has published a packet specification and an experimental Python userspace tool for related FocalTech chips.

However its documented **2808:6658** interface is **vendor-specific (class 0xFF)**, at high speed, with **512-byte** bulk packets on endpoints `0x01` and `0x82`. Our **2808:5955** enumerates as **CDC Data (class 0x0A)**, at full speed, with **64-byte** maximum packet sizes.

The shared endpoint *numbers* and chipset-name similarities are insufficient to establish matching protocols. **Do not send that project's registers, reset, firmware, power or scan commands to 2808:5955.** Compare packet construction against the matching Windows MOH DLL first.

The [OMGrant/ft9201-libfprint](https://github.com/OMGrant/ft9201-libfprint) project may offer reusable techniques for implementing a `libfprint` driver with a vendor matching engine, but it also targets different hardware and should not be installed for this device unchanged.

## Next research tasks

1. Trace the Windows MOH driver's **finger status** request and response semantics.
2. Verify whether finger status can be read without additional initialisation or configuration.
3. Only then add a single, explicitly confirmed status query to the hardware tool.
4. Keep firmware writes, register writes, resets and power-mode changes out of the prototype.
