# FocalTech fingerprint readers on Linux

**Experimental Linux support for FocalTech USB fingerprint reader `2808:5955`.**

The long-term goal is a **fully open-source driver and native matcher** with standard Linux `libfprint` / `fprintd` integration. The code and findings are organised so that other developers can investigate additional FocalTech USB readers—and potentially SPI models—without assuming they use the same protocol.

> **Project status — 14 October 2026:** Live USB image capture and experimental fingerprint enrolment **work** on the original `2808:5955` under Nobara. An isolated FocalTech Windows matching-engine bridge has also successfully enrolled 12 captures, temporarily committed a template to mock storage, and matched **4/4 held-out same-finger images offline**. A GUI completed live enrolment with **12 usable and 4 rejected touches**. **Live verification, real different-finger rejection, secure persistent storage and system login/unlock are not yet implemented.** The Windows DLL is a **temporary research dependency**, not the intended final driver.

For the precise current capabilities and known-good call sequence, read **[Current status and safety boundaries](docs/current-status.md)**.

## What works, and what does not

| Component | Status |
| --- | --- |
| USB device identification, handshake, finger contact/release, image capture | **Demonstrated on physical hardware** |
| Live lift-and-press enrolment GUI | **Experimental success**; temporary in-memory template, never installed for login |
| Windows match-on-host engine via isolated Linux compatibility bridge | **Working research reference**, requires an external proprietary DLL |
| Offline same-finger template verification | **4/4 held-out matches** with consistent image polarity |
| Offline polarity-mismatch rejection | **4/4 no-match outcomes** when the verification polarity differed |
| Real different-finger security test | **Still required** |
| Fully native/open-source feature extraction, matching and template engine | **Under development**; several independent image components and synthetic tests exist |
| `libfprint`, `fprintd`, KDE screen unlock, PAM login or `sudo` | **Not available** |

The offline results are a proof of the processing path, **not a measured false-accept rate**. The original and inverted grayscale representations both matched when used consistently; the inverted one generally yielded higher quality scores and is the present GUI default.

## Hardware tested

| Item | Identified value |
| --- | --- |
| USB vendor/product | `2808:5955` |
| Device revision | `20.03` (`bcdDevice`) |
| USB endpoints | Bulk OUT `0x01`, bulk IN `0x82` |
| Intermediate raw image | 10,240 bytes (5,120 little-endian 16-bit samples) |
| Current processed image | 64 × 80 grayscale pixels |
| Matching Windows package | FocalTech MOH 5.10.66.6611 |
| Verified Linux host | Nobara (Fedora-based) |

These findings are **device-specific**. Other FocalTech sensors can have different interfaces, firmware commands, dimensions, calibration and host-vs-sensor matching arrangements.

## Trying the project

Most development currently happens on **`feature/ft5955-moh-engine-bridge`**. The default `main` branch does not yet contain all of the working experimental code.

```bash
git clone --branch feature/ft5955-moh-engine-bridge \
  https://github.com/Inforce855/focaltech-5955-linux.git
cd focaltech-5955-linux
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

**Safe offline regression tests** (no real biometric data, USB requests or proprietary DLL execution):

```bash
make -C native test
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

**Live experimental enrolment GUI** (opt-in, acts on the physical USB sensor):

```bash
# Requires a supported Linux desktop/Tkinter, bubblewrap, GCC, binutils
# and your own legally obtained matching FocalTech driver ZIP.
sudo -v
.venv/bin/python tools/interactive_enroll_gui.py \
  --archive /path/to/7_Fingerprint-module.zip --send
```

Run the GUI as a **regular user**, not as root. Only its short-lived USB capture helper requests `sudo -n`. Lift your finger fully between touches. Each capture batch is bounded to eight images; use **Continue** for another batch. The engine executes in a separate bubblewrap sandbox with no direct USB or network access; template storage is temporary and cleared on exit. The experimental workflow does **not** enrol a system-login fingerprint.

For individual utilities and which ones are only historical experiments, see **[Tool and test index](docs/tool-index.md)**. For the guarded Windows-engine bridge and supported local tests, see [MOH bridge engineering notes](docs/5955-moh-engine-bridge.md).

## Project organisation

| Location | Purpose |
| --- | --- |
| [`tools/`](tools/) | Live GUI, sensor acquisition, offline playback, isolation runners and diagnostic experiments |
| [`engine/`](engine/) | Experimental Linux compatibility shim for the proprietary Windows MOH DLL |
| [`native/`](native/) | Independent C image-processing and future open-source matching components |
| [`tests/`](tests/) | Synthetic protocol, shim, converter and Python regression tests |
| [`docs/current-status.md`](docs/current-status.md) | Evidence-backed current capabilities and limitations |
| [`docs/roadmap.md`](docs/roadmap.md) | Short current development roadmap |
| [`docs/tool-index.md`](docs/tool-index.md) | Which script does what; current vs research-only |
| [`docs/archive/`](docs/archive/) | Preserved earlier README and roadmap research logs |

The original extensive README and roadmap have **not been discarded**: [historical README](docs/archive/readme-research-log-2026-10-14.md) and [historical roadmap](docs/archive/roadmap-research-log-2026-10-14.md). Other detailed research notes remain in [`docs/`](docs/).

## Privacy, security and limits

- **Never** publish fingerprint captures (RAW, PGM, PNG), Windows biometric records, templates, user USB traces containing biometric payloads or proprietary driver binaries. Real local captures belong under gitignored `local-data/`.
- Tests and live probes are experimental. Do not use match scores or a successful GUI enrolment as evidence of secure authentication.
- No PAM, KDE login, `fprintd`, firmware or production biometric database changes are made by the described GUI.
- Do not substitute commands from another FocalTech product ID without device-specific analysis.
- The `engine/` compatibility code includes material adapted under LGPL-2.1-or-later; see [its licence](engine/COPYING.LGPL-2.1). **A project-wide licence has not yet been chosen**; contributions should account for the different source provenance.

## Next priorities

1. Live verification of a newly enrolled finger, including genuine different-finger rejection and repeated-session testing.
2. Harden the privileged USB interface, process isolation and persistent protected template storage.
3. Develop a genuinely native, distributable matcher to remove the proprietary Windows DLL dependency.
4. Integrate with `libfprint` / `fprintd`; only after validation, offer **opt-in** KDE/PAM use while retaining password recovery.
5. Factor out transport and device profiles before extending support to other USB or SPI FocalTech models.

More detail: **[Roadmap](docs/roadmap.md)**.
