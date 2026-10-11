# Image acquisition: current MOH DLL findings

Status: **static analysis only for image acquisition**. The actual `2808:5955` has not yet returned image pixels. Finger-contact status and firmware information were verified separately on Nobara on 11 October 2026.

The matching Windows binary is `FtWbioDriverUmdfV3.dll` from the MOH 5.10.66.6611 driver archive, held locally (not redistributed).

## 1. The GetImage function

At preferred-image VA `0x180006B74`, `CBiometricDevice::ff_sc_GetImage`:

- Expects an existing device-initialised flag and a caller-supplied destination buffer.
- Reads one-byte dimensions from device object offsets `+0x5A` and `+0x5B`.
- Checks caller's image buffer size against **width × height**.
- Allocates **2 × width × height** bytes as its intermediate acquisition buffer.
- Calls helper `0x18000793C` to populate that buffer.
- Optionally normalises/adjusts samples, then calls separate image conversion functions:
  - special path `0x18000510C` if dimensions are **152 × 40**;
  - general path `0x180005C78` for other geometry.
- Copies/produces image information into the caller's output.

**Important:** The 152 × 40 comparison is a code branch, not proof that the physical `2808:5955` has that resolution. The Windows driver supports more than one model. Similarly, apparent 16-bit raw samples do not prove the final sensor image format without a capture.

## 2. Bulk image-read request

The intermediate buffer helper at `0x18000793C`:

- Issues logical command **`0x81` with no payload** through the same `ff_sc_WriteData` infrastructure already used for the successful firmware-info and finger-status requests.
- After a successful write, calls `ff_sc_ReadData` with a requested size **2 × width × height**.

The corresponding candidate USB command frame, if this is the same already-verified USB transport, is `02 00 01 81 80` (BCC = `00 ^ 01 ^ 81 = 80`).

**Do not send that request yet.** A full scan may require activation and readiness checks; receiving large framed data may require multiple USB IN transfers. The existing short-response probe is unsuitable for imaging. A partial scan could expose private biometric data.

## 3. Image geometry comes from the device

At preferred-image VA `0x180008328`, the Windows driver obtains width and height instead of assuming they are fixed:

1. Calls the shared read helper `0x180007B8C` with selector **`0x03`**, response length **1**, output at device structure offset **`+0x5B`**. This is the candidate *height* field.
2. Calls that helper with selector **`0x04`**, length **1**, output at offset **`+0x5A`**. This is the candidate *width* field.
3. Multiplies the two one-byte values and stores the pixel count at `+0x5C`.

Helper `0x180007B8C` issues logical command `0x80` with two payload bytes `[selector, read length]`, then expects a one-byte response.

The complete **candidate metadata packets** are:

| Query | Logical command | Payload | Full USB OUT bytes |
| --- | --- | --- | --- |
| Height (offset `+0x5B`) | `80` | `03 01` | `02 00 03 80 03 01 81` |
| Width (offset `+0x5A`) | `80` | `04 01` | `02 00 03 80 04 01 86` |

Neither query has been tested on the physical sensor. Both are inferred to be metadata reads; their real effects are not yet guaranteed.

## 4. Higher-level image capture is not just GetImage

The capture/scan path at approximately `0x18000CC0C` appears to do additional work **before** calling `ff_sc_GetImage`:

- calls helper `0x180009E80` while preparing image scanning;
- calls device-mode operation `0x180008500` with argument `0x06`;
- checks readiness through `0x180009B94` with a bounded retry loop;
- allocates the output buffer, then invokes `ff_sc_GetImage` at `0x18000CE5B`.

The protocol effects of these operations are not yet independently validated. **Do not invent a shortcut by sending `0x81` without understanding them.**

## 5. Next controlled hardware test (no image capture)

`tools/image_geometry_probe.py` performs a *single* explicitly confirmed image geometry read on the exact same device/revision/interface. By default it is offline only.

```bash
# Fetch latest code, then dry-run only
.venv/bin/python tools/image_geometry_probe.py --dimension height
.venv/bin/python tools/image_geometry_probe.py --dimension width

# One actual metadata request at a time; type SEND for each
sudo .venv/bin/python tools/image_geometry_probe.py --dimension height --send
sudo .venv/bin/python tools/image_geometry_probe.py --dimension width --send
```

If the two replies are valid one-byte values, we'll learn the reported pixel resolution and likely `2 × width × height` raw acquisition size. Do not repeatedly query or force image-acquisition until the results have been reviewed.

No fingerprint image/template should be committed to the public repository. If image capture is eventually implemented, use private local files only and avoid displaying/logging raw pixel hex to terminals or issue trackers.

## Live image-height query — 11 October 2026

**Confirmed on the physical FocalTech 2808:5955 reader:**

- Command (bulk OUT, 7/7 bytes): `02 00 03 80 03 01 81`.
- Response (bulk IN, 7 bytes): `02 00 02 04 40 46 00`.
- Declared data length: `0x0002` (response type `04` and one-byte result `40`).
- XOR checksum: `00 ^ 02 ^ 04 ^ 40 = 46` — **valid**.
- Extra trailing `00` matches the pattern from earlier verified responses.
- Reported image **height: 64 pixels** (`0x40`).

The image width is **not yet known**. Do not assume a resolution of 80 × 64 or infer a byte count until the width query succeeds. This is a metadata response, not fingerprint image data.

**Next hardware test:** one explicit width query (`--dimension width --send`), after which calculate `2 × width × 64` bytes as the Windows driver's expected intermediate acquisition buffer size. The number of USB transfers needed will depend on protocol framing and transfer behaviour.

## Live image-width query — 11 October 2026

The sensor confirmed the other metadata dimension:

- USB OUT: `02 00 03 80 04 01 86` (7/7 bytes sent).
- USB IN: `02 00 02 04 50 56 00` (7 bytes received).
- Payload `0x50` = **80 pixels wide**, with validated BCC `0x56` and one trailing `00` byte.
- Previous height query returned `0x40` = **64 pixels high**.

**Verified image geometry: 80 × 64 = 5,120 pixels.** From the Windows driver's two-byte intermediate sample format, the likely raw image buffer is **10,240 bytes (10 KiB)**, excluding any transport headers/trailers and any final converted output. This is not a captured fingerprint image.

The special 152 × 40 processing branch in the DLL therefore does not match the dimensions returned by this specific reader; the general processing path should apply.

**Next:** reverse-engineer scan setup, readiness checks, and multi-transfer framing before testing the image-read command. The raw image must stay private and local.

## Further trace of Windows scan preparation (11 October 2026)

After validating the sensor's actual `80 × 64` geometry, the disassembly of the image capture caller around preferred-image VA `0x18000CC0C` provides several more concrete clues:

1. It calls setup helper `0x180009E80` with argument `0`. That helper invokes `0x180009D80`, which issues logical command **`0x34`** (no payload) and reads **two bytes**. The helper checks for **`0xAA55`** in the returned 16-bit word and can perform additional retries/operations if the first attempt fails. Whether the bytes arrive as `55 AA` or in another interpretation still requires verification; do not assume the word value is literal wire order.
2. The capture caller then invokes mode helper `0x180008500` with mode argument **`6`**. That branches through `0x180008780` (preparation) and `0x1800080C0`, which sends logical command **`0x87`** with three payload bytes. For that branch the code passes a `0x40` setting. The full effects are not yet established and may alter sensor power/scan state.
3. The caller waits 10 ms and checks readiness with `0x180009B94`, up to a bounded number of attempts. That helper uses logical command **`0x80`** to request a **two-byte** value and tests it against **`0x5AA5`**. The request is not the same as our already-confirmed width/height selectors.
4. Only after these steps does the caller allocate a `width × height` output buffer, invoke `ff_sc_GetImage` (`0x180006B74`), then consume/convert the result. The inner raw-image helper `0x18000793C` requests `2 × width × height` bytes via logical command **`0x81`**.

**Do not send these commands or automatically sequence them yet.** The firmware-info/geometry tests prove the transport frame for short metadata replies, not this stateful acquisition path. In particular, the current `receive_reply` routine is designed for tiny responses and cannot receive the 10,240-byte sample buffer correctly.

Next engineering work: independently validate the scan/setup command payloads, establish what states are modified and how to restore idle mode, and implement a length-bounded multi-transfer reader that rejects malformed frames without logging or publishing biometric samples.
