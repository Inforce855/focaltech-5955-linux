# FocalTech 2808:5955 — live libfprint enrolment bridge (experimental)

This uses the **real sensor**, *not* prerecorded or synthetic fingerprint images.
The existing, bounded `tools/auto_contact_capture.py` helper captures only
fresh OFF→ON contacts, at most eight frames or 240 status polls per session.
The new bridge converts each 64×80 little-endian raw capture through the
existing native-v3 normaliser (default), enlarges with bicubic interpolation
by 10×, and sends 640×800 greyscale bytes to libfprint's virtual-image socket.

The live bridge has NOT been run against physical 2808:5955 hardware or a
compiled libfprint in the development environment. Its private helper framing,
conversion to 640×800, and socket packet formatting passed synthetic-only
unit tests. Its output is *experimental*; enrolment may fail. Do **not** use
for login, PAM, KDE unlock or any access-control decision.

## 1. Unpack into the existing project

From `~/Projects/focaltech-5955-linux`:

```bash
mkdir -p "$HOME/Projects/focaltech-5955-linux"
tar -xzf "$HOME/Downloads/focaltech-5955-live-libfprint.tar.gz" \
  -C "$HOME/Projects/focaltech-5955-linux"
```

Use the actual download location if different. Archive entries are only
`tools/...`, `tests/...`, and `docs/...`; nothing modifies system libraries.

## 2. Build an isolated libfprint (once)

Install **development packages** (not the distro libfprint itself):

```bash
sudo dnf install git meson ninja-build gcc gcc-c++ pkgconf-pkg-config \
  glib2-devel libgusb-devel libgudev-devel openssl-devel pixman-devel
```

Then:

```bash
cd ~/Projects/focaltech-5955-linux
bash tools/build_isolated_libfprint.sh
make -C native build/ft5955_normalize_cli
.venv/bin/python -m pip install opencv-python-headless
.venv/bin/python -m unittest discover -s tests -p test_live_libfprint_bridge.py -v
```

This builds upstream libfprint tag **v1.94.10** under
`~/Projects/libfprint-ft5955-src` and `~/Projects/libfprint-ft5955-build`,
with **only** the `virtual_image` driver. It NEVER runs `meson install`,
replaces the system library, or changes fprintd/PAM.

## 3. Enrol using real fingers, in TWO terminals

**Terminal 1** — isolated libfprint front end:

```bash
cd ~/Projects/focaltech-5955-linux
bash tools/run_isolated_enroll.sh
```

Select a finger when the upstream example asks. Leave the terminal open
until it requests the first scan. It should say `Virtual image device for debugging`.

**Terminal 2** — bridge to real hardware:

```bash
cd ~/Projects/focaltech-5955-linux
sudo -v
.venv/bin/python tools/live_libfprint_bridge.py
```

Lift your finger fully, touch lightly, lift again for the next stage.
The sensor is integrated with the PC's power button: do **not** push the
physical switch. Live messages in Terminal 1 are **libfprint's own**
enrolment stages and retry feedback. Terminal 2 prints sensor state and
how many complete impressions were passed across the socket.

The helper stops after **eight real impressions** or two minutes of polling.
If libfprint is still enrolling, relaunch Terminal 2 for another bounded
session with your finger lifted. You can cancel with Ctrl+C.

To try the original little-endian percentile conversion instead of the
native-v3 path, use the alternative bridge mode:

```bash
.venv/bin/python tools/live_libfprint_bridge.py --processing contrast
```

Do not treat a successful enrolment as a validated match; follow up with
independent verification and impostor rejection before any real integration.

## Privacy and generated files

* No `.raw`, PNG, fingerprint descriptors or templates are written **by the bridge**.
* The **upstream `examples/enroll` program** can write `enrolled.pgm`
  (fingerprint image) and `test-storage.variant` (sensitive biometric template).
  The runner uses a private `0700` folder, `umask 077`, beneath the existing
  Git-ignored `local-data/libfprint-live/` directory.
* **Never** commit or upload fingerprint images, the template file, or the
  socket contents. Do not paste the raw binary terminal output if the example
  fails unexpectedly.
* The virtual-image driver is **not** the physical FocalTech driver yet. This
  verifies live capture, conversion and libfprint acceptance before writing
  a permanent `FpImageDevice` transport driver.
