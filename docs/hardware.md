# Hardware and Windows driver findings

## Device observed on Nobara Linux

The following values were obtained from `lsusb`, `lsusb -v` and `lsusb -t` on 11 October 2026:

- `ID 2808:5955 FocalTech FocalTech Fingerprint Device`.
- USB full-speed device (12 Mbit/s).
- `bcdDevice 20.03`: a reported USB device revision, **not proof** of firmware version.
- One interface, number 0: class `0x0a` (CDC Data), subclass `0`, protocol `0`.
- Bulk **OUT** endpoint `0x01` (maximum packet size 64 bytes).
- Bulk **IN** endpoint `0x82` (maximum packet size 64 bytes).
- `lsusb -t` showed `Driver=[none]` for that interface.
- Nobara's `libfprint 1.94.100-1.fc44` and `fprintd 1.94.5-5.fc44` were installed, but `fprintd-list "$USER"` returned `No devices available`.

A 64-byte `wMaxPacketSize` is a USB transfer characteristic, **not** the proprietary application protocol frame length.

## Matching Windows driver

Examined locally from the manufacturer's archive; these binaries must not be redistributed.

- MOH package: `FocalTechFPSSOdriver25H2x64V5.10.66.6611_WHQL`.
- Driver INF: `FtWbioDriverUmdfV3.inf`.
- The INF explicitly lists `USB\VID_2808&PID_5955`, alongside `2808:C6D5` and `2808:65D5`.
- The INF refers to Microsoft's WinUSB infrastructure and `FtWbioDriverUmdfV3.dll`.
- DLL strings contain `FT9366`, `UsbTarget::BulkWrite`, `ff_sc_ReadData` and `ff_sc_CalcBCC`. These are **leads for protocol analysis**, not confirmation of the specific chip model or command format.
- The separate MOC/FT9365 package targets other device IDs; it must not be assumed compatible.

## Questions to investigate

1. Actual silicon/controller identification and firmware version.
2. Does the device emit data before host initialisation?
3. Command framing, status codes and integrity checks.
4. Genuine safe read-only queries, discovered rather than guessed.
5. Image acquisition versus match-on-chip functionality.
6. Relationship, if any, to other reverse-engineered FocalTech devices.

## Protocol research precautions

Use documentation, lawful analysis of the Windows driver and/or USB traces captured on personally controlled hardware. Do not upload biometric data, proprietary binaries, or captured enrolment templates. Avoid untested OUT commands and firmware writes.
