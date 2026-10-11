# Recovered USB packet framing — static analysis

**Status:** firmware-info command and response **verified on physical FocalTech 2808:5955 on 11 October 2026**. Other commands remain untested.

The relevant Windows DLL is `FtWbioDriverUmdfV3.dll`, SHA-256 `b2dd3b0a5c79c9a9bc628ccbfdbd20b83e63799d9d310ae513c378c7af1b958e` (MOH 5.10.66.6611). Binary not distributed.

## How the correct branch was identified

The Windows DLL checks the enumerator string **USB** versus **ACPI** (function preferred-image VA `0x18000640C`). It selects mode 1 for USB and mode 2 for ACPI. The USB branch registers a virtual method table containing the frame writer (`0x18000EB60`) and reader (`0x18000ECC0`). The ACPI branch has separate similar methods. The user's `2808:5955` is a USB device, so the USB branch is the relevant candidate.

## Outgoing frames

From the USB writer at `0x18000EB60`:

| Offset | Meaning |
| --- | --- |
| 0 | Constant `0x02` |
| 1–2 | 16-bit **big-endian** length = payload bytes + 1 |
| 3 | One-byte logical command |
| 4 onward | Optional payload |
| Last byte | XOR of **all preceding bytes except byte 0** |

Total frame size: `5 + payload_length`. The function assembles the frame and passes it to the USB write helper at `0x180011ACC`. It retries a failed transmission.

The firmware-information function (`0x180006FD8`) invokes command `0x30` with zero payload (`0x18000702C`). The reconstructed frame is:

```text
02 00 01 30 31
│  └┬──┘ │  └─ XOR(00, 01, 30) = 31
│   │    └─ firmware information logical command 30
│   └─ length = one command byte and no payload
└─ header 02
```

This packet was initially reconstructed from machine instructions and was later **verified on physical hardware**: sending exactly these five bytes to endpoint `0x01` returned the firmware-information response documented below. Other commands must not be extrapolated without tracing the DLL.

## Incoming frames

USB response parser (preferred-image VA `0x18000ECC0`):

- Decodes bytes 1–2 as a **big-endian length**.
- Checks that the reply fits the caller's buffer and length is not zero.
- Requires **response type `0x04` at byte 3**, else returns an error.
- Copies payload from byte 4; the caller-visible payload size is *declared length − 1*.
- Verifies the trailing XOR against bytes 1 through the last payload byte.
- Does **not clearly verify byte 0** in this inspected path; do not assume what byte 0 must be.

The firmware info caller allows a 63-byte buffer (passes `0x3F` to the reader) and interprets successful payload as text, inspecting it for `APP`.

### First real reply captured from Nobara

The reader accepted the single firmware-information query, returning these bytes:

```text
02 00 2e 04
46 54 39 33 36 78 5f 41 50 50 5f 46 57 33 30 33
32 5f 55 53 42 5f 44 45 43 5f 53 56 30 2e 35 5f
35 38 34 39 5f 50 6f 77 65 72 4b 65 79
51 00
```

The length `0x002e = 46` is **one response-type byte** plus **45 data bytes**. Thus the self-contained frame is 50 bytes: header (1), length (2), type (1), payload (45), BCC (1).

- Response type: `04`.
- Payload (ASCII): `FT936x_APP_FW3032_USB_DEC_SV0.5_5849_PowerKey`.
- XOR of bytes 1 through 48: `51`, matching the BCC in byte 49.
- **Byte 50 is an extra `00`** outside the length-declared, checksum-protected frame. Its meaning remains unknown.

The initial Python parser required exactly 50 bytes and rejected the observed 51 bytes. The updated parser checks the declared length and BCC strictly, but tolerates exactly one trailing `00` following the valid frame. This was a **software decoder error**, not a hardware failure.

## Offline tooling

```bash
python3 tools/protocol_codec.py
python3 -m unittest discover -s tests -v
```

The offline codec itself cannot access USB. Unit tests include both synthetic cases and the **real firmware-information response**, including checksum and trailing-byte checks. The physical response was acquired separately with the opt-in `tools/firmware_probe.py`.

## Next steps

1. Trace the **finger-status** request in the Windows DLL, including any required setup and the expected response.
2. Introduce new hardware commands only after careful static analysis and explicit user confirmation.
3. Keep firmware updates, resets and register writes out of the prototype.
