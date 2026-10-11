# FocalTech 5955 Linux

Reverse-engineering and Linux userspace support for the **FocalTech USB fingerprint reader, VID:PID `2808:5955`**.

**Project status: First physical 80 × 64 fingerprint image files reported working under Nobara (11 October 2026)!** USB communication, contact detection, image geometry, handshake, readiness and image-sized transfers have been demonstrated. Distinct fingers produce visibly different images; repeated captures of the first finger look similar. **Visual observations are not automated identity matching, and no functional `libfprint` driver exists yet.** The device is visible on Linux but was not recognised by `libfprint 1.94.100` and `fprintd 1.94.5` on Nobara (Fedora 44 base).

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

**First real USB test: SUCCESS on 11 October 2026.** The command reconstructed from the manufacturer's Windows MOH DLL was sent once to the actual sensor. It returned a valid firmware-information packet (50 framed bytes followed by an additional 00 byte). The sensor identified itself as `FT936x_APP_FW3032_USB_DEC_SV0.5_5849_PowerKey`.

```bash
# Inspect the request without contacting the sensor:
.venv/bin/python tools/firmware_probe.py

# Only if you accept the experimental hardware risk:
sudo .venv/bin/python tools/firmware_probe.py --send
```

The live mode requires typing **SEND** before any bulk OUT transfer. It refuses a mismatched USB device revision or endpoint configuration, never detaches a kernel driver, sends **exactly one** five-byte request to endpoint `0x01`, and reads at most two times from `0x82` with bounded timeouts. There are no command retries, firmware writes, resets, authentication changes or enrolment procedures.

**Do not rerun the live request just to check the decoder**: the captured response has been added to the offline regression tests. A valid USB reply proves a working exchange, not fingerprint detection or matching. Review any raw data before posting publicly.

## Experimental finger-status query (NOT YET HARDWARE-VERIFIED)

The matching Windows MOH DLL's `ff_sc_ReadFingerStatus` routine constructs command `0x82` with payload bytes `73 01`, requests one response byte, and returns that byte to its caller. Using our verified frame encoder, this generates `02 00 03 82 73 01 f3`.

This is a **separate, unverified command** from the proven firmware-information request. The name suggests it reads status, but we cannot guarantee side effects until it has been tested against this sensor.

The first recommended experiment is **one reading with no finger on the sensor**:

```bash
# Dry-run: no hardware access
.venv/bin/python tools/finger_status_probe.py

# Explicitly opt-in to ONE command; type SEND at the prompt
sudo .venv/bin/python tools/finger_status_probe.py --send --label no-finger
```

If the first response is safe and meaningful, a later run with `--label finger` can be used with a finger resting on the reader *before* confirming. The test **never polls**, resets the sensor, enrols fingerprints, attempts authentication, or interprets a status byte as finger-present without evidence. It reuses the strict USB device safety checks and bounded response handling from the verified firmware probe.

The routine's caller checks one response value (`0x05`), but whether this identifies finger contact is **unknown**. We need to compare no-finger and finger-present results.

## Investigating image acquisition

The matching Windows driver implements `ff_sc_GetImage`. Static analysis shows that it reads **two bytes per pixel** into an intermediate buffer, processes that data into an output image, and first obtains image **width** and **height** from the sensor.

We have **not captured any fingerprint image** from the physical device yet. The image read command is a candidate `02 00 01 81 80` (logical `0x81`), but Windows performs separate setup and readiness checks before calling it. Do not send that command directly.

A safer next test is to ask the sensor for its image dimensions using the read helper found in the Windows DLL:

```bash
# Offline preview (does not access USB)
.venv/bin/python tools/image_geometry_probe.py --dimension height
.venv/bin/python tools/image_geometry_probe.py --dimension width

# Hardware: one command each, asks you to type SEND
sudo .venv/bin/python tools/image_geometry_probe.py --dimension height --send
sudo .venv/bin/python tools/image_geometry_probe.py --dimension width --send
```

These are still experimental commands, reconstructed from the matching Windows MOH DLL and not yet tested on the live sensor. The tool checks the device's exact USB identity and revision, sends one request per run and never records images.

See [GetImage reverse-engineering notes](docs/image-acquisition-research.md) for technical details and the next work required.

## Producing a real fingerprint image file

**First physical fingerprint image files are now reported working (11 October 2026).** The sensor reports 80 × 64 pixels, and the Windows DLL reads a 10,240-byte intermediate sample buffer. Initial image transfer returned 10,246 bytes and was rejected due to an unrecognised extra byte; a subsequent checksum-first decoder allowed one unknown trailer after verifying the frame. User testing of Finger A, Finger B and Finger A again gave visually similar first/third images and a visibly different second image. These are user's observations, not independent inspection or a verified fingerprint matching algorithm.

An **offline, private PNG converter** is available now: [`tools/raw_to_png.py`](tools/raw_to_png.py). It cannot query hardware itself. Once a real 10,240-byte capture exists in the ignored `local-data/` directory, run:

```bash
.venv/bin/python tools/raw_to_png.py local-data/capture.raw
```

By default it produces both byte-order interpretations (unverified until inspected). For each: the lossless 80 × 64 16-bit greyscale image, a contrast-stretched 80 × 64 PNG, and a 640 × 512 enlarged PNG preview. All output files are written privately with mode `0600`, without overwriting existing files. They are ignored by Git and must not be uploaded publicly.

### Scan handshake confirmed on real hardware

On 11 October 2026, `tools/scan_handshake_probe.py` sent `02 00 01 34 35` once and received the correctly framed and checksummed `55 aa` payload: the Windows driver's expected **`0xAA55` handshake**. This was not an image scan.

### Next diagnostic: read the scan-readiness status (not yet hardware tested)

The matching MOH DLL also contains a separate readiness read: logical `0x80`, selector `0x01`, two bytes. It compares the returned little-endian word to `0x5AA5` **after enabling scanning mode**. The isolated read is a reasonable diagnostic, but may return a different status before scanning has been enabled.

```bash
# Dry run: no device access
.venv/bin/python tools/scan_ready_probe.py

# Optional one-shot readiness query with manual SEND confirmation
sudo .venv/bin/python tools/scan_ready_probe.py --send
```

The candidate packet is `02 00 03 80 01 02 80`. This probe does not set the device's scan mode, attempt a capture, or save biometric samples. Its behaviour on the physical device remains unverified, so avoid repeated or unconfirmed commands. See [acquisition notes](docs/image-acquisition-research.md) for the verified handshake and limitations.


### First live image-sized response: 10,246 bytes

On 11 October 2026, the physical reader answered one `0x81` request with **10,246 bytes**, consistent with 10,240 candidate sample bytes, five bytes of framed transport and one additional byte. The first decoder deliberately rejected the response because that extra byte was **not** the `00` seen in earlier short replies; **no image was saved and the large-frame checksum has not yet been confirmed**.

The patched `tools/image_transfer.py` accepts a nonzero single-byte trailer **only if the preceding 10,245-byte image frame passes the exact length, type and XOR checksum checks**. It will still reject a corrupt or malformed response. An accepted frame indicates recovered sample data, **not yet a proven fingerprint image**. We can check whether it looks like a ridge pattern after private conversion to PNG.

### Experimental first fingerprint image transfer — one-shot `0x81`

The scanner has now returned a valid `0x5AA5` readiness marker **without an explicit scan-mode change**. We have added [`tools/image_capture_probe.py`](tools/image_capture_probe.py) as a cautious *first attempt* to retrieve the Windows DLL's expected **10,240-byte** raw image buffer, without issuing the separate `0x87` mode-control command:

```bash
cd ~/Projects/focaltech-5955-linux
git pull --ff-only

# Dry run: prints planned command, does not touch USB
.venv/bin/python tools/image_capture_probe.py

# One experimental physical image request, with confirmation
sudo .venv/bin/python tools/image_capture_probe.py --send
```

Touch the reader lightly (it is also the PC's power button) and type **`CAPTURE`**. This transmits **one** `02 00 01 81 80` request to the audited USB device, then reads only a tightly bounded IN response. The large response format and command's behaviour on this hardware are **not yet verified**, so a timeout or a short status response is possible and is not grounds for blind retries. This command may initiate temporary sensor acquisition state despite not issuing a `0x87` mode change.

If and only if exactly 10,240 sample bytes arrive (either unframed as the Windows data reader might expose them or in a validated, checksummed frame), the tool creates a private, new `local-data/fingerprint_DD-MM-YYYY_HH-MM-SS.raw` file. It never prints image bytes, never overwrites an earlier capture, and attempts to assign ownership back to the original `sudo` user for local inspection. `local-data/` is already ignored by Git. An *unframed* response has no transport checksum and requires further validation.

Run the locally prepared offline converter **without sudo**, substituting the filename reported by the capture utility:

```bash
.venv/bin/python tools/raw_to_png.py local-data/fingerprint_DD-MM-YYYY_HH-MM-SS.raw
```

It creates native 80 × 64 16-bit PNGs, enhanced 8-bit versions and 640 × 512 previews. Endianness, contrast and whether the capture contains a usable fingerprint remain to be verified on a real image. Do not attach or commit biometric image files to a public issue, PR or repository.

### First physical fingerprint image files (11 October 2026)

After updating the frame decoder to check the full 10,245-byte frame independently of its extra trailing byte, the device owner confirmed successfully producing image files from **three captures**: first finger, different finger, then the original finger. The first and third images appeared similar, and the second image appeared substantially different. This is promising evidence of finger-dependent sensor imagery, **not a measured false-accept/reject rate or completed enrolment/verification**.

The fingerprint images, native raw buffers and generated PNGs were **not uploaded or committed to GitHub**. The actual 16-bit sample endianness, image orientation, conversion quality, ridge definition, and matching reproducibility remain to be assessed. Recommended next step is *private/offline* image-quality and repeatability analysis before attempting any authentication integration.

## Safety and scope

- Aim: an independently implemented Linux userspace driver, preferably integrated into `libfprint` / `fprintd`.
- Verify protocol before transmitting anything to the reader.
- Keep the proprietary Windows driver archive and binaries **outside this public repository**.
- Avoid firmware flashing and any PAM, KDE or system-library changes while prototyping.
- No compatibility claim is made for other FocalTech product IDs.

See [live hardware findings](docs/protocol-research.md) and [wire-frame details](docs/usb-frame-format.md).

## Contributions

Hardware reports and independently developed protocol notes are welcome. Do not redistribute proprietary binaries or biometric samples.

No project licence has been chosen yet; substantial code contributions should wait until a licence is agreed.
