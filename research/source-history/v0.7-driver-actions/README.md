# FocalTech 2808:5955 — libfprint driver action glue v0.7

**Experimental integration source, not yet a complete libfprint driver.**

Prior evidence: the real MOH engine can enrol, export a template, restart and verify; v0.6.1 verified a versioned synthetic MOH template can round-trip through **the user's real private libfprint** `FpPrint` API. This package supplies the previously missing callback mapping and enforces stage counts.

## Contents

- `ft5955_action_core.[ch]`: independent state machine, 12 *accepted* stages, attempts limits (96/16), quality retry, exactly-once complete, cancel and match/no-match. Supports direct v0.4 MOH responses (`PROGRESS n 12`, `RETRY QUALITY`, `COMPLETE`, `MATCH`, `NO_MATCH`). Rejects skipped/repeated stages, malformed data and wrong-operation responses.
- `ft5955_fpi_action_bridge.[ch]`: main-thread libfprint callbacks using `fpi_device_enroll_progress/complete`, `fpi_device_verify_report/complete`, `fpi_device_get_enroll_data`, and the tested FpPrint envelope. Quality rejects leave the accepted count unchanged. On final enrolment only, an already-committed vendor template and subfactor are turned into a serialisable FpPrint.
- `ft5955_fpi_print_bridge.[ch]`, `ft5955_print_codec.[ch]`: copied unchanged from the successful v0.6.1 test.
- `tests/test_action_core.c`: synthetic state and wire-result regression tests; `tests/test_print_codec.py`: v0.6.1 codec tests.
- `run_action_tests.sh`: local C regression; `check_private_headers.sh`: compile-only libfprint callback-API check against your isolated source; `run_fpprint_test.sh`: already validated v0.6.1 FpPrint test.

## Tests (safe: no sudo, USB, fingerprint captures, DLL or system install)

```bash
bash run_action_tests.sh
bash run_tests.sh
bash run_fpprint_test.sh
bash check_private_headers.sh
```

`run_action_tests.sh` and `run_tests.sh` passed in the development environment. `run_fpprint_test.sh` succeeded on the user's private libfprint when run previously with v0.6.1; v0.7 is the same codec. **The new `check_private_headers.sh` has NOT yet run on the user's Nobara private libfprint and its compile result is pending.** Our environment does not have GLib headers to compile that module here.

## Integration boundary: DO NOT install this as an operational fingerprint driver yet

The caller must implement/retain ALL of the following in the existing private `focaltech_5955.c`:

1. A libfprint `FpDevice` subclass with `.enroll`, `.verify`, `.cancel` (and suitable open/close) and exactly 12 enrol stages. Retain the **working native** USB handshake/finger-status implementation, no untested USB commands.
2. Nonblocking **asynchronous** fresh finger OFF -> ON capture and the tested image pipeline (raw 10,240-byte LE16 -> percentile 8-bit -> invert). The existing PyUSB helper is a reference for the safe audited packet sequence; it is not automatically callable from native USB callbacks.
3. Vendor DLL MUST remain in the checked, isolated `bubblewrap` subprocess; *never* dlopen it in libfprint's process. Blocking IPC belongs in a worker, not the device's main context. Make sure worker cancellation/timeout kills and reaps that subprocess and that no callback can access a freed device.
4. Marshal validated MOH engine events back into libfprint's main context. Invoke `ft5955_fpi_apply_reply()` once for each bounded v0.4 text reply *on the main context*; it parses and validates the wire protocol using `ft5955_action_consume_reply()` and then emits the libfprint callback. Do not call `ft5955_action_consume_reply()` separately on the same action.
5. Obtain a committed vendor template and subfactor from the sandbox in RAM **before** reporting final enrol success. `ft5955_fpi_apply_event` calls `ft5955_print_pack` then attaches the versioned envelope to libfprint's enrol `FpPrint`.
6. For verification, validate the stored `FpPrint` with `ft5955_fpprint_extract` and import its template into a **fresh** MOH engine, then supply a newly captured (inverted) finger frame. Report match vs no-match; a quality retry does not mean authentication failure. A corrupt print or engine failure must NEVER report MATCH.
7. Support prompt cancellation, no persistent session files, bounded tries/time, sensitivity-aware memory wiping and controlled shutdown. Never enable system fprintd/PAM/KDE login until the full driver passes real tests and at-rest template security is addressed.

### Important design detail

`ft5955_fpi_apply_reply()` performs **one** state transition and **one** callback emission per bounded MOH response. The portable test can call `ft5955_action_consume_reply()` separately, but the native driver must not duplicate transitions. This remains an integration module, **not** an automatic drop-in installation.

To merge into the actual native driver, the current `~/Projects/libfprint-ft5955/libfprint/drivers/focaltech_5955.c` source is needed, specifically its device state, USB transfer callbacks and class initialisation. Do not blindly replace that file with a generic template.
