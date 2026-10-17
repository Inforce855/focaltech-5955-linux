# FT5955 isolated MOH IPC adapter v0.2

This is **not yet a libfprint driver**. It adapts the already-existing and tested `tools/test_moh_isolated_live_identify.sh` sandbox runner to a small, bounded local binary IPC protocol. Its purpose is to validate the real-engine boundary before writing libfprint enrolment callbacks.

No driver files, Git repositories, system libraries, fprintd, PAM or USB firmware are changed. No USB device is opened by this adapter. The working `interactive_enroll_gui.py` and `live_finger_identify.py` remain untouched.

## Synthetic regression test (safe, no fingerprint data)

```bash
cd ~/Projects/ft5955-moh-ipc-v0.2
python3 test_adapter.py
```

Tests two full 12-stage enrolments, rejected samples, two matches, no-match, ambiguous, quality retry, cancellation and a new session. The fake runner never accesses actual fingerprints or the vendor DLL.

## Actual vendor engine (still no USB; needs an explicit private frame-producing client)

Run the adapter as your normal user, **not root**:

```bash
cd ~/Projects/ft5955-moh-ipc-v0.2
python3 moh_adapter.py \
  --runner "$HOME/Projects/focaltech-5955-moh-test/tools/test_moh_isolated_live_identify.sh"
```

The vendor runner defaults to the SHA-pinned, root-owned DLL at `/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll`. Its existing bubblewrap isolation and DLL integrity checks remain in force. The binary protocol is not suited to typing manually; use a dedicated client once integrated. **Do not send biometric data to the synthetic fake runner.**

### Wire protocol

All text commands end with `\n`. `SAMPLE` and `VERIFY` must each be followed **immediately by exactly 5,120 bytes** (64×80 unsigned 8-bit greyscale), with no second delimiter. The image must use the working GUI's `to_8bit(decode_samples(raw, 'little'))` conversion **and** its in-memory inversion `255 - pixel`, at enrolment and verification alike. Output lines are bounded, text-only responses. Frame data is never logged or persisted by this adapter.

`HELLO` -> `READY 2`; `BEGIN 1` or `BEGIN 2` -> `BEGIN OK`; `SAMPLE` -> `PROGRESS n 12`, `RETRY QUALITY` or `COMPLETE`; `VERIFY` -> `MATCH 1`, `MATCH 2`, `NO_MATCH`, `AMBIGUOUS` or `RETRY QUALITY`; `CANCEL` -> `CANCELLED`; `QUIT` -> `BYE`.

The *current vendor runner* has a fixed two-slot, memory-only model. This prototype does **not** attempt to serialise templates or support a general fprintd database. Enrolment of slot 2 requires slot 1 to be complete; successful `VERIFY` requires **both** slots complete. `CANCEL` destroys the engine process and its temporary templates.

## Remaining integration work

1. Refactor the existing MOH sandbox runner to accept one or more stored templates via a secure, bounded IPC interface, without breaking the reference tools.
2. Connect the live USB capture sequence and callback state machine in the native `FpDevice` development branch; cancellation must stop outstanding USB operations.
3. Implement `FpPrint` serialization and protected template import/export, then verify cross-process restart and rejection of other fingers before trial fprintd integration.
4. Do not enable PAM/KDE authentication or replace the system libfprint library.

**Security limitations:** caller-supplied samples are processed by an experimental proprietary engine in bubblewrap. The current engine uses incomplete compatibility shims; all results are diagnostic only. stdout returns classifications, never a security decision. Never upload raw captures, templates, or the vendor DLL to GitHub.
