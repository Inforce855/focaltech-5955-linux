# FT5955 MOH integration boundary — v0.3 (14 October 2026)

**Development only. No libfprint enrolment callback or production authentication is implemented.**

This extends v0.2 with two independent integration experiments while keeping
`focaltech-5955-moh-test` and `libfprint-ft5955` UNCHANGED:

1. `native/ft5955_ipc.[ch]`: native C process/IPC client for **future use
   inside a libfprint `FpDevice` driver**. It starts `moh_adapter.py`,
   exchanges bounded commands and exactly 5,120-byte frames, enforces
   response timeouts and decodes progress/retry/match classifications.
   Calls are **synchronous** and must execute in a cancellable worker context,
   NOT directly in libfprint's GLib main thread. No persistent templates.
2. `live_capture_client.py`: optional user-authorised, live **diagnostic**
   linking the known-good USB helper, proven Windows-like inverted conversion,
   v0.2 adapter and sandboxed vendor matcher. Two fingers are enrolled in
   separate bounded batches and can then be identified. No sensitive output
   or files, no PAM/KDE/fprintd changes. Real sensor/hardware operation has
   **not** been tested in this development container.

The code does not install a library, modify git repos, touch fingerprint
configuration or grant access to anything. Only running `--live` explicitly
can access the USB hardware. No biometric samples are bundled.

## Synthetic tests (NO USB, NO DLL)

Run from the unpacked `ft5955-moh-ipc-v0.3` directory:

```bash
bash native/run_tests.sh
python3 test_adapter.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: C integration PASS, original adapter `OK`, two additional Python
capture-protocol tests `OK`. The tests exercise two 12-stage enrolment sequences,
quality retry, C result decoding, cancellation and two-finger identification,
using only explicitly synthetic frames and a fake engine.

`native/ft5955_ipc.c` is intended to be compiled into a subsequent private
libfprint development build, rather than installed or called from the shell.
Link it into a worker-thread device operation, not into libfprint's main loop.
It is not yet wired into `focaltech_5955.c` and therefore cannot be used by
`fprintd-enroll` or `fprintd-verify`.

## Optional real-hardware MOH integration regression

The current *working reference checkout* must exist at
`~/Projects/focaltech-5955-moh-test` (feature branch), including the source
and unit-tested installed vendor DLL. On your own Nobara machine, **as your
normal user**, only if intentionally testing real fingerprints:

```bash
cd ~/Projects/ft5955-moh-ipc-v0.3
sudo -v
python3 live_capture_client.py --live
```

- This is a two-finger **RAM-only** experimental test, not registration for login.
- Use **two different fingers**. Each needs 12 accepted touches; lift fully and
  reposition between captures. Enter starts a bounded 8-touch/240-poll helper
  session, `q` cancels and wipes temporary templates.
- The program imports `prepared_pixels` from the existing working
  `tools/live_finger_identify.py`, which implements precisely the original
  64×80 16-bit little-endian contrast conversion followed by `255-pixel`
  inversion; both enrolment and verification use that same preprocessing.
- Engine isolation, DLL hash validation and no-network/no-USB access in the
  DLL process remain the responsibility of the **original trusted**
  `tools/test_moh_isolated_live_identify.sh`.
- The vendor engine and its compatibility shims are experimental and
  proprietary. Do not use its outputs for login or other access decisions.
- No raw samples, images or templates are written by this bundle, but runtime
  biometric data travels through the local helper and IPC process memory.
- If the helper reports errors, stop instead of automatically retrying.

## Next driver milestone

Driver transport calls must move the **already-audited** bounded USB capture
protocol into the new `FpDevice`, with asynchronous work and cancellation.
The driver will use the result decoder as follows: accepted `PROGRESS n 12`
means `fpi_device_enroll_progress`, `RETRY QUALITY` means a retryable error,
`COMPLETE` must **NOT** call `fpi_device_enroll_complete` yet because the
current MOH runner only keeps templates in process-local RAM and does not
return a usable persistent `FpPrint`. Templates must first be exported,
serialised, securely imported, and verified against *fresh* finger scans
in a new process. Driver must never claim successful persistent enrolment
without a usable `FpPrint`.

Preserve the existing working MOH GUI and two-finger tool. Do not put raw
captures, templates or vendor DLLs on GitHub. Do not change PAM or the system
libfprint/fprintd installation.
