# FT5955 MOH / libfprint FpPrint serialization test — v0.6

14 October 2026. **No actual driver enrolment callbacks in this version.**

## Verified hardware baseline

v0.5's real hardware test succeeded in completing 12 accepted impressions, creating and validating a versioned proprietary MOH template in memory, importing it into a fresh isolated sandbox and reporting both `MATCH 1` and `NO_MATCH` on live verification touches. The operator did not label each verification touch in the pasted log, so no numerical false-reject/false-accept rate can be inferred. No persistent templates were written.

## What changed

- Updated `ft5955_fpi_print_bridge.[ch]` guards against wrong driver, device-stored prints, repeated assignment, malformed variant type and corrupt/invalid template envelope.
- A new standalone **actual private libfprint** test, `tests/fpprint_roundtrip.c`, runs the public `fp_print_serialize`/`fp_print_deserialize` functions against an `FPI_PRINT_RAW` print with **synthetic** vendor-template bytes and checks the recovered metadata, subfactor and payload.
- `run_fpprint_test.sh` builds and runs the new test against the **user's private** `~/Projects/libfprint-ft5955/build-ft5955` .so without installing or touching system libraries, fprintd, PAM, KDE or USB.
- Portable codec test scripts from v0.5 are included. The C GLib/FpPrint test is provided for execution on the user's Nobara machine, because the construction environment lacks GLib/libfprint development files; **it is not yet claimed passing**.

The standalone ABI test uses the writable `fpi-type` GObject property because the internal `fpi_print_set_type()` may not be exported from the private libfprint shared library. When the bridge is compiled as a driver source *inside* libfprint, it calls `fpi_print_set_type()` normally. This arrangement is for testing only, not a stable public plugin API.

## Run on Nobara (no sudo, no USB)

```bash
cd ~/Projects
tar -xzf ~/Downloads/ft5955-moh-libfprint-v0.6.tar.gz
cd ft5955-moh-libfprint-v0.6
bash run_tests.sh
bash run_fpprint_test.sh
```

If the real library test fails, paste only the **terminal error output** (no raw images, template files or engine dumps). The private libfprint source is not present in the development environment, so local ABI/build mismatches need fixing against your exact checkout. The fingerprint template in this test is synthetic and is never written to a file.

## Remaining work

A real libfprint `FpDevice` driver must handle asynchronous fresh-touch capture, cancellation, 12 accepted impressions, returning this FpPrint from `fpi_device_enroll_complete()`, and using the restored FpPrint for verify/identify with a fresh MOH sandbox. The vendor engine must remain isolated. The SHA-256 digest on the vendor envelope detects accidental damage but does **not** encrypt or authenticate templates. Never enable fprintd/PAM login from this prototype; persistence, at-rest protection, repeated negative controls and error recovery remain unverified.
