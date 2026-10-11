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

This supports a likely **XOR-based block check character (BCC)**. It does *not* tell us which bytes in a command are covered, where the check byte is placed, or whether all commands use this checksum. No live packet format has yet been recovered.

## Related project: research only, not a compatible driver

The project [inevitableDivu/focaltech-2808-6658-driver](https://github.com/inevitableDivu/focaltech-2808-6658-driver) has published a packet specification and an experimental Python userspace tool for related FocalTech chips.

However its documented **2808:6658** interface is **vendor-specific (class 0xFF)**, at high speed, with **512-byte** bulk packets on endpoints `0x01` and `0x82`. Our **2808:5955** enumerates as **CDC Data (class 0x0A)**, at full speed, with **64-byte** maximum packet sizes.

The shared endpoint *numbers* and chipset-name similarities are insufficient to establish matching protocols. **Do not send that project's registers, reset, firmware, power or scan commands to 2808:5955.** Compare packet construction against the matching Windows MOH DLL first.

The [OMGrant/ft9201-libfprint](https://github.com/OMGrant/ft9201-libfprint) project may offer reusable techniques for implementing a `libfprint` driver with a vendor matching engine, but it also targets different hardware and should not be installed for this device unchanged.

## Next research tasks

1. Trace the MOH DLL's outgoing USB transfer call sites to recover packet headers, lengths and integrity check coverage.
2. Identify the matching incoming response parser, including error/status handling.
3. Determine whether device startup requires a host-to-device initialisation sequence.
4. Verify one **read-only information request** from multiple independent clues before enabling it in the test app; ideally corroborate using a user-controlled Windows USB capture.
5. Leave experimental firmware writes, register writes, reset and power-mode commands out of the Linux test application.
