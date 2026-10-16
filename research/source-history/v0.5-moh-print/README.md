# FT5955 — versioned MOH template / prospective FpPrint payload (v0.5)

14 October 2026. **Experimental development only. Not a working libfprint or fprintd driver.**

## What v0.4 established

The user successfully enrolled a finger, exported a vendor MOH template, shut down
its isolated process, restarted a new verified sandbox, and identified the
original finger while receiving NO_MATCH for other fingers. No persisted
biometric data was needed. The known-good GPIO/USB acquisition, 64×80 inverted
contrast-processing path and isolated MOH engine remain unchanged.

## What v0.5 actually adds

- **A versioned 5955-specific binary envelope** intended to become a
  `FPI_PRINT_RAW` / `fpi-data` payload in libfprint. It encodes the actual
  vendor MOH template bytes, subfactor, VID/PID (2808:5955), algorithm and
  inverted-polarity version. It accepts 1..1,048,576 template bytes.
- A SHA-256 integrity digest (to catch accidental corruption; **NOT** a MAC,
  signature, confidentiality layer or defence against deliberate replacement).
- Strict rejection of corrupt, truncated, oversized, wrong-device, wrong-
  algorithm, wrong-polarity or unknown flags; no saving fingerprint files.
- `ft5955_print_codec.[ch]`: portable C codec for the future native driver;
  `print_codec.py`: Python cross-check/test harness.
- `ft5955_fpi_print_bridge.[ch]`: **uncompiled integration source** showing how
  a real libfprint driver would use `fpi_print_set_type(FPI_PRINT_RAW)` and
  the internal `fpi-data` `GVariant` property. This code is NOT copied into
  your running libfprint worktree and has NOT been compiled against its headers.
- An optional live experiment repeating v0.4's restart, this time placing the
  vendor template into the new versioned envelope *in RAM*, validating it,
  and then restoring to a fresh MOH engine. Still not a real FpPrint object.

The expected libfprint design is **host-matched RAW**: the enrolled template
is host-side data, **not** an ID stored on the sensor. Do not call
`fpi_print_set_device_stored(..., TRUE)`.

## Run the offline tests — no USB, sudo or proprietary DLL

```bash
cd ~/Projects/ft5955-moh-print-v0.5
bash run_tests.sh
```

`gcc`/`cc` and OpenSSL development headers are needed for the cross-language
C codec tests (`openssl-devel` on Nobara). The synthetic C process-restart test
also needs the previously installed v0.4 project at
`~/Projects/ft5955-moh-template-v0.4` (otherwise that test skips).

Five tests passed in our isolated development container: format roundtrip,
invalid/corrupt inputs, bounds, compiled C/Python byte compatibility, and
synthetic template reuse in a freshly started C engine process.

## Optional real-hardware in-memory roundtrip

Only if you wish to exercise the exact v0.5 envelope around the previously
validated v0.4 restart sequence:

```bash
cd ~/Projects/ft5955-moh-print-v0.5
sudo -v
python3 fpprint_boundary_live.py --live
```

The script uses the *existing* feature worktree and **v0.4** sandbox runner.
It enrols a single finger for 12 accepted impressions, wraps its temporary
vendor template in a versioned, SHA-256-checked in-memory print blob,
terminates the old MOH process, unwraps the blob and imports it into a new
sandbox, then permits same-finger and other-finger checks. Enter starts a
bounded capture batch, `q` ends the experiment. No biometric files are saved.
All real USB accesses use the existing `sudo -n` bounded helper; the caller
is the normal desktop user.

**Even if successful, this is not cross-reboot persistence or a real
`fp_print_serialize()`/`fp_print_deserialize()` test.** It demonstrates the
payload we intend to put inside an FpPrint, NOT the surrounding libfprint
metadata, enrol/verify callbacks or fprintd storage.

## FpPrint integration guide (future private driver branch)

The internal libfprint print API exposes `FPI_PRINT_RAW` and the `fpi-data`
`GVariant` property. The plan is:

1. On successful MOH 12-stage commit, call the native codec to wrap the
   vendor template, then `ft5955_fpprint_assign(enroll_print, blob, n)`.
   Afterwards report libfprint enrolment completion.
2. The fprintd/libfprint storage layer would serialise the FpPrint, not the
   standalone `.raw` or proprietary MOH data files. Verify using the *actual*
   `FpPrint` restored from storage, call `ft5955_fpprint_extract()`, load its
   template/subfactor into a fresh isolated MOH process, and evaluate a fresh
   inverted 64×80 fingerprint impression.
3. Correctly map `RETRY QUALITY`, `MATCH`, `NO_MATCH`, cancellation, corrupted
   data, adapter failure and ambiguous identification to libfprint APIs.
4. Test cancellation, reconnects, cross-process and cross-reboot persistence,
   multiple user/finger records, template permissions and negative controls
   **before** any production fprintd/PAM/KDE integration.

Open issues: libfprint GLib bridge code must be compiled and tested on your
installed private source tree, the asynchronous `FpDevice` callbacks have not
been implemented, adapter process isolation and restart remain experimental,
and unencrypted FpPrint/template data is sensitive. The integrity digest is
not authentication and does not prevent forged or substituted data.

No file in this archive modifies your repositories, `/usr/local`, system
libraries, fprintd or PAM. Never upload or commit real fingerprint templates,
raw images or the proprietary Windows DLL.
