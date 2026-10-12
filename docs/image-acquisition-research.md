# Image acquisition: current MOH DLL findings

Status: **first live image files reported successful under Nobara** on 11 October 2026 after correcting frame parsing to checksum-validate the payload before tolerating one extra byte. The user reports three physical captures—finger A, finger B, finger A—and visually similar first/third images with a clearly different second. The images themselves have not been independently inspected or published; fingerprint template matching and authentication remain unimplemented.

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
2. The capture caller invokes mode helper `0x180008500` with mode argument **`6`**. **Correction (12 October 2026):** static branch tracing shows this selects `0x6C`, **not `0x40`**. The mode-7 branch, instead, selects `0x40`. Mode 6's code reaches `0x1800080C0`, which sends logical command **`0x87`** with three payload bytes. The command's effects and safe idle restoration remain unverified; it must not be sent to the live device.
3. The caller waits 10 ms and checks readiness with `0x180009B94`, up to a bounded number of attempts. That helper uses logical command **`0x80`** to request a **two-byte** value and tests it against **`0x5AA5`**. The request is not the same as our already-confirmed width/height selectors.
4. Only after these steps does the caller allocate a `width × height` output buffer, invoke `ff_sc_GetImage` (`0x180006B74`), then consume/convert the result. The inner raw-image helper `0x18000793C` requests `2 × width × height` bytes via logical command **`0x81`**.

**Do not send these commands or automatically sequence them yet.** The firmware-info/geometry tests prove the transport frame for short metadata replies, not this stateful acquisition path. In particular, the current `receive_reply` routine is designed for tiny responses and cannot receive the 10,240-byte sample buffer correctly.

Next engineering work: independently validate the scan/setup command payloads, establish what states are modified and how to restore idle mode, and implement a length-bounded multi-transfer reader that rejects malformed frames without logging or publishing biometric samples.

## Offline PNG tooling and next handshake test

On 11 October 2026, the original Windows MOH DLL was inspected locally with `llvm-objdump` to confirm the image capture control flow. A private, offline image converter has been added at `tools/raw_to_png.py`, with synthetic converter tests. It was tested offline with a non-biometric gradient: the generated images opened correctly as 80 × 64 16-bit grayscale, 80 × 64 8-bit contrast enhanced, and 640 × 512 PNG preview. **This is not a hardware fingerprint image.**

The user's actual fingerprint image has **not yet been acquired**. The raw intermediate buffer is expected to be 10,240 bytes, but whether the samples are big-endian, little-endian, linearly mapped or polarity-inverted remains unverified. The converter preserves 16-bit values and generates both endian interpretations for later inspection. Output remains in ignored `local-data/` with private file permissions.

The Windows helper at VA `0x180009D80` sends logical command `0x34` with no payload, then requests a two-byte response. The code compares its little-endian word to `0xAA55`. The corresponding candidate framed command is:

```text
02 00 01 34 35
```

The newly added `tools/scan_handshake_probe.py` can **optionally** send this one request with explicit confirmation, without entering image-acquisition mode or attempting any fingerprint capture. This command is still untested against the physical reader. If it returns the expected `55 aa` payload, that corroborates our understanding of a scan-path handshake. It does not by itself establish that the later mode-change, readiness poll or `0x81` image request can be run safely.

Next priorities: verify handshake response; reconstruct the 0x87 scan-mode payload and idle restoration; implement strictly bounded 10,240-byte framed acquisition to a private file; use offline converter to make and inspect the genuine PNG. Do **not** publish captured fingerprint pixels or templates.

## Live scan-handshake confirmation — 11 October 2026

**Verified on FocalTech USB 2808:5955:** the single-command handshake probe returned the exact two-byte word expected by the Windows MOH DLL.

- USB OUT: `02 00 01 34 35` — **5/5 bytes** written to EP `0x01`.
- USB IN: `02 00 03 04 55 aa f8 00` — **8 bytes** received from EP `0x82`.
- Declared frame length: `0x0003` = response type `0x04` plus the two payload bytes `55 aa`.
- Little-endian payload word: **`0xAA55`** — exactly matches the comparison in the matching Windows DLL at `0x180009E36`.
- XOR check byte: **`0xF8`** (`00 ^ 03 ^ 04 ^ 55 ^ aa`) — verified.
- The final `00` is the same out-of-frame trailer already observed on previous responses.

**Interpretation:** USB packet construction and the two-byte handshake response have now been confirmed on hardware. This is not a scan or a fingerprint capture. It does not verify that scan-mode activation or image reads can run safely without further state handling.

### Next candidate: read-only readiness register query (not yet tested)

The Windows DLL's readiness routine at preferred-image VA `0x180009B94` passes selector `0x01`, requested length `0x02` to the shared logical `0x80` read helper (`0x180007B8C`). It then checks the returned **little-endian** 16-bit word against `0x5AA5`. The reconstructed on-wire request would be:

```text
02 00 03 80 01 02 80
```

The equivalent response payload for the expected ready state is `a5 5a` (if the response follows the already-confirmed framing). **A pre-scan test may not report readiness until the device is placed into scan mode**, so a different reply is not necessarily an error. No mode-changing or image-acquisition command should be sent on that basis.



## Live readiness query confirmed — 11 October 2026

The physical FocalTech 2808:5955 replied to the reconstructed selector 01, length 02 readiness query with the **exact** marker expected by the Windows DLL.

- OUT: `02 00 03 80 01 02 80` — 7/7 bytes.
- IN: `02 00 03 04 a5 5a f8 00` — 8 bytes.
- Payload `a5 5a` interpreted as little-endian gives **`0x5AA5`**.
- XOR BCC `f8` validates the response, followed by the previously observed `00` trailer.
- **No explicit scan-mode change was made.** That means the register's marker also appears during the current idle/no-explicit-scan condition; it does **not** prove a fresh fingerprint image is ready.

### First bounded image-read experiment (unverified on hardware)

Windows low-level image helper at `0x18000793C` transmits logical `0x81` with no payload and asks its read abstraction for `2 × 80 × 64 = 10,240` sample bytes. Candidate OUT bytes: **`02 00 01 81 80`**. An opt-in one-shot command can attempt this read **without** enabling the state-changing `0x87` scan mode, deliberately preferring a failed/no-data result over a guessed mode configuration. Image transfer framing is unverified. Only an exactly sized raw transfer or a valid, checksummed 10,240-byte framed payload should be retained, with data saved privately in ignored local-data; never print or commit fingerprint samples. Failure does not authorise blind retries or mode changes.



## First live image-sized transfer — 11 October 2026

**The physical reader responded to the first one-shot `0x81` request with a full image-sized USB transfer, but no fingerprint file was saved:**

```text
USB OUT: 02 00 01 81 80   (5/5 bytes written)
USB IN:  10246 bytes
Parser:  "Reply length implies 10245 bytes (optionally one observed 00 suffix), but got 10246."
```

For an 80 × 64 image with 16-bit intermediate samples, the candidate response structure is:

- **10,240 bytes** of possible image sample payload.
- **5 bytes** total protocol framing (start byte, 2-byte length, reply type, XOR checksum).
- **1 extra byte** beyond the framed length.
- Total **10,246 bytes**, precisely the response length observed.

The previous decoder would only trim that extra byte if it were `0x00`. Since it rejected this transfer with a *length* error, the last byte was **not** `0x00`. We have **not confirmed that the frame checksum passes**, whether the extra byte is a trailer or some other information, or whether the response contains a usable live fingerprint. The old probe correctly did not save any biometric data. Do not infer fingerprint success from length alone.

A narrowly scoped decoder fix now checks a 10,245-byte frame **independently**, confirming declared image-payload length `10240`, reply type `0x04`, prefix `0x02`, and XOR BCC. It permits **at most one** further byte of **unknown meaning** only *after* the entire image frame passes those checks; malformed/truncated/oversized transfers and bad checksums continue to be rejected. Valid samples are saved only to private `local-data/`, and no raw pixel content is printed.

**Next:** one operator-authorised repeat of `sudo .venv/bin/python tools/image_capture_probe.py --send` after `git pull --ff-only`, light finger contact, and typing `CAPTURE`. If the checksummed frame validates, the probe should save a private `.raw` file ready for `tools/raw_to_png.py`. If it fails validation, stop and examine **only non-biometric metadata** (packet length, declared frame size, checksum result), not the raw samples.


## Physical image-file milestone — 11 October 2026

After applying the updated `tools/image_transfer.py` parser and using the private capture/PNG conversion workflow, the device owner reported successful generation of **several physical fingerprint image files** under Nobara Linux:

1. Finger A image.
2. Different finger (Finger B): visually very different from Finger A.
3. Finger A again: visually similar to the first capture.

This is the first report of actual finger-dependent image files from the Linux prototype. It is **user-reported visual evidence** rather than an independently reviewed biometric image, a verified byte-order/polarity mapping, or an evaluated matcher. No biometric samples were placed in the public repository and no copies are requested.

This milestone supports moving from transport reverse-engineering to local-only quality checks: compare same-finger versus different-finger samples while accounting for contact pressure, translation and rotation; confirm which 16-bit endian interpretation produces coherent ridges; then investigate host-side enhancement and matching. Do not turn on KDE/PAM biometric authentication until enrolment and matching have been validated with a password fallback.


## FT6206 touchscreen 0x87 cross-check and mode-6 correction (12 October 2026)

A separate FocalTech FT6206/FT5x06 capacitive **touchscreen** controller
datasheet assigns I²C **register address `0x87`** to
`TIMEENTERMONITOR`, the delay before an idle controller transitions
from Active to Monitor mode. Adjacent registers include `0x86`
(automatic mode transition) and `0x88` / `0x89` (active/monitor
reporting periods). Confirmed in the 2010 FT5x06 application note
<https://threefivedisplays.com/wp-content/uploads/datasheets/touch_driver_datasheets/FT5x06_REV_0_7_REG.pdf>
(section 2.1.15, PDF page index 13) and the FT6206 application note
<https://www.buydisplay.com/download/ic/FT6206.pdf>.
**This is a different chip family and interface**; coincident hexadecimal
values do not establish the same register map or firmware semantics.

Read-only inspection of the **matching 2808:5955 MOH Windows sensor DLL**
`FtWbioDriverUmdfV3.dll` provides stronger, independent evidence:

- `0x18000cd44`: the scan caller passes **mode number 6** to
  `0x180008500`.
- `0x180008530`–`0x180008577`: the mode selector branches by mode value.
  The **mode-6** branch is at `0x18000865a` and sets
  **`0x6c`** at `0x180008679`–`0x180008689`.
  The different **mode-7** branch (`0x18000859d`–`0x180008609`)
  uses **`0x40`**. Earlier research notes mistakenly attributed
  `0x40` to mode 6; this is now corrected.
- `0x1800080e6`–`0x180008101`: the command writer loads
  **`CL=0x87`**, with a **three-byte payload** built as
  `[selected_value, 0x01, selected_value]`. For the mode-6 branch,
  the corresponding *static* payload would be
  `[0x6c, 0x01, 0x6c]`.
- That `0x87` goes to the existing proprietary **USB framed command
  writer** `0x180008004`; it is not an I²C register-address operation
  like the FT6206 touchscreen use of `0x87`. The three payload bytes'
  individual sensor-side meaning is still unknown.

**Conclusion:** The touchscreen document is interesting background about
FocalTech's power/mode terminology, but offers **no verified explanation**
for the missing 5955 scan rows and is **not** a command reference for the
fingerprint reader. Do not try to access FT6206 register `0x87` on the
5955, transmit this statically recovered state-changing USB command, or
modify scan/idle/autosuspend states based on this resemblance.
Prioritise further non-executing analysis of sensor preparation and
idle restoration.

## Static Windows acquisition-readiness recheck (12 October 2026)

Context: the owner observed intermittently missing **entire sensor rows**
in valid 10,240-byte raw frames. Among three four-capture sessions,
11 Oct 14:24 A1 had 9 leading all-zero rows, 11 Oct 14:55 B1 had
5, and 12 Oct 00:47 A1 had 16. Other captures had no all-zero rows;
some had smaller zero regions, including at the bottom. Every one
was an operator-authorised discrete image request. USB sysfs reported
`power/control=on`, `runtime_status=active`: normal USB autosuspend
was disabled, so that is not an adequate explanation.

### Confirmed directly from matching MOH Windows driver

Read-only disassembly of the **matching PID 5955 MOH package**
`FtWbioDriverUmdfV3.dll`, extracted from the user's previously
provided `7_Fingerprint-module.zip`. The DLL was **not executed**.
Relevant preferred-image x64 virtual addresses:

| Call site | Observation | Interpretation/limit |
|---|---|---|
| `0x18000cc49`–`0x18000cc76` | Capturing caller invokes an imported device-service callback before setup. | Exact higher-level meaning still unknown. |
| `0x18000cce0`–`0x18000ccea` | Calls helper `0x180009e80` with argument 0. | This is more than direct image reading. |
| `0x180009ef2`–`0x180009f47` | Helper performs prior handshake check (`0x180009d80`), can issue another internal operation and sleep 1 ms on a bounded retry path. | Its precise scan-controller side effects are **not** safely established. |
| `0x18000cd41`–`0x18000cd53` | Sets mode `6` through helper `0x180008500`. | That mode follows preparation at `0x180008780` and an `0x87` logical command through `0x1800080c0`; **state-changing, not tested on PID 5955**. |
| `0x18000cd93`–`0x18000cdb3` | `Sleep(10)` then `0x180009b94`, with the counter initialised to six; failure loops. | At most six checks spaced by ~10 ms (+USB/computation), *not* an unbounded retry. |
| `0x180009bc1`–`0x180009c65` | The readiness helper reads selector `01`, length `02` with logical `0x80` and compares little-endian return to `0x5AA5`. | The device **also returned `0x5AA5` in an idle/no-explicit-mode test**. Therefore this alone is *not a proven freshly captured frame-complete signal*. |
| `0x18000cdf0`–`0x18000ce5b` | Only after readiness success does caller allocate output and call `0x180006b74` once. | **One host-side image extraction call** per passage; multiple sensor-side internal exposures remain unknown. |
| `0x180006c65`–`0x180006c81`, `0x180007967`–`0x1800079e9` | The inner image routine allocates 2 bytes per sensor sample, sends logical `0x81` and reads that buffer. | This is the same image request our prototype uses, but without the full state sequence. |

The sleep import is confirmed from the PE `KERNEL32.dll` import table:
the call through IAT `0x180019090` resolves to `Sleep`. No inference
from the timing alone proves that the sensor itself captures multiple
frames. **Multi-impression enrollment** (lift/reposition across stages)
is a separate concept from multiple internal exposures per capture.

### Hypothesis and safe next steps

An underspecified scan start/ready sequence could plausibly explain
intermittent zero-filled image rows **despite full checksummed USB packets**.
However, the data also fits contact/masking or other sensor-side timing
behaviour; no root cause is proven. Distinguish three stages:
(1) status `0x82 73 01` detecting contact (`05` present, `06` absent),
(2) Windows capture *preparation/scan state*, and (3) image buffer `0x81`.
Neither status `05` nor `0x5AA5` by itself establishes a full image.

**No device commands have been added or tested as a result of this trace.**
Next work is read-only reconstruction of mode-6 state transitions,
failure/idle restoration and a non-invasive image-quality gate on stored
captures; only after the effects and safe rollback are understood
should a controlled operator-approved hardware experiment be considered.
Never automatically send `0x87`, modify USB configuration or retry blindly.

## First guarded capture preflight using verified commands (12 October 2026)

New experimental tool: [`tools/scan_preflight_capture.py`](../tools/scan_preflight_capture.py).
The owner suggested moving toward a more Windows-like acquisition path
after observing 5, 9 and 16 all-zero leading rows in otherwise complete
sensor frames. The owner explicitly authorised a controlled initialisation
test. This **first stage** reuses commands that were **individually observed
to work** on the exact physical 2808:5955; it does **not** implement the
complete Windows mode-control sequence.

The script opens one explicitly validated USB interface, then performs:

1. **Exactly one** established `0x34` handshake, validate reply `0xAA55`.
2. **Exactly one** established `0x82 73 01` finger-presence query,
   require reported status `0x05` before proceeding.
3. A 10-ms host-side delay, then **exactly one** established
   `0x80 01 02` readiness query, validate `0x5AA5`.
4. **Exactly one** already-tested `0x81` image read, with the existing
   bounded USB receiver, strict framed payload validation, and private
   ignored `local-data/` storage. Report only zero percentage and
   blank-row counts using **64×80 little-endian** raw sample geometry.

**Limitations:**

- **DOES NOT send logical `0x87`**, firmware, resets, untested setup
  commands or any other newly inferred packets. `0x87` mode-6 writes
  and reliable idle rollback remain under static investigation.
- The Windows driver also performs preparation *before* mode 6, which
  this script does not reproduce. The readiness marker `0x5AA5` was
  already observed in idle mode, so validating it cannot establish
  that a new exposure is complete or that initialization succeeded.
- The host's 10-ms delay tests neither firmware internal settling nor
  multiple sensor-side scans. The three read-only-query operations are
  only individually characterised; **their combination is an experiment**.
- Every request is opt-in (`--send` plus typing `CAPTURE`), no retries,
  no automatic polling; unexpected values abort further requests.
- One-frame output alone cannot establish statistical improvement.
  Compare blank-row counts against the previous 12 captures without
  claiming that any differences prove causality.

**Nobara synthetic-only tests (no USB):**

```bash
cd ~/Projects/focaltech-5955-linux
git pull --ff-only
python3 -m unittest discover -s tests -p test_scan_preflight_capture.py -v
```

**Single opted-in live trial, only after tests pass:**

```bash
sudo .venv/bin/python tools/scan_preflight_capture.py --send
```

Place a finger gently on the sensor, then type `CAPTURE`. If finger
status is absent or any reply is malformed, it **does not send `0x81`**.
On successful retrieval it prints only total zeros and number of
leading/total/trailing all-zero rows, saves a private RAW file, and
returns. Do not upload any RAW/PNG data or run undocumented mode writes.
