# Recovered USB packet framing — static analysis

**Status:** analysed from the user's Windows MOH driver; **not yet tested on physical hardware**.

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

**This is reconstructed from machine instructions, not a captured USB transfer. Do not transmit it blindly.**

## Incoming frames

USB response parser (preferred-image VA `0x18000ECC0`):

- Decodes bytes 1–2 as a **big-endian length**.
- Checks that the reply fits the caller's buffer and length is not zero.
- Requires **response type `0x04` at byte 3**, else returns an error.
- Copies payload from byte 4; the caller-visible payload size is *declared length − 1*.
- Verifies the trailing XOR against bytes 1 through the last payload byte.
- Does **not clearly verify byte 0** in this inspected path; do not assume what byte 0 must be.

The firmware info caller allows a 63-byte buffer (passes `0x3F` to the reader) and interprets successful payload as a NUL-terminated firmware-information string, inspecting it for `APP`. The exact version text on the physical sensor is unknown.

## Offline tooling

```bash
python3 tools/protocol_codec.py
python3 -m unittest discover -s tests -v
```

The codec cannot access USB. It builds a candidate command and validates **synthetic** reply frames. Unit tests do not prove the hardware accepts any request.

## Next steps before live queries

1. Confirm that `0x180011ACC` maps to the correct USB bulk OUT pipe and `0x18001177C` to bulk IN using WDF pipe handles.
2. Verify the driver does not perform mandatory wake/initialisation before requesting firmware information.
3. Add an **explicitly opt-in**, read-only hardware firmware-information query with a short timeout and no retry storm.
4. Keep firmware updates, resets and register writes out of the prototype.
