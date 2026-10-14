# FT5955 v0.9.4 — live verification safety results (14 October 2026)

The user ran the standalone diagnostic against the **private** libfprint FT5955 driver. All twelve enrolment stages completed successfully, with two rejected enrolment scans correctly not counted (at stages 3 and 9). Fingerprint data stayed in RAM.

## Verification cancellation — PASS

The diagnostic started verification with the finger OFF and called `GCancellable` after approximately three seconds. Libfprint returned `G_IO_ERROR_CANCELLED`; the reader closed/reopened and then successfully completed its USB descriptor, 0x34/0xAA55 handshake and ABSENT finger-status check at 17:08:29. These observations establish cancellation/recovery of the verification operation, not every possible cancellation path.

## Deliberate quality rejection — functional path PASS; diagnostic counter BUG

The test-only proxy discarded the first captured verification frame and returned `RETRY QUALITY`; the patched driver logged:

```text
libfprint-Message: 17:08:42.280: FT5955 scan rejected; lift and reposition finger
Quality probe: callbacks=1, errors=0, driver_retry_messages=0, result=MATCH.
FAIL: expected exactly one internal retry, then one successful match.
```

The driver's retry message is visible, the same verification operation subsequently returned `MATCH`, and there was one match callback with zero callback errors or libfprint assertion. This **supports successful recovery from the forced internal quality rejection**. The diagnostic's final FAIL arose because `tools/native_verify_safety_v094.c` attached its `g_log_set_handler` to the wrong domain (`libfprint-focaltech_5955`) while the retry message actually uses GLib log domain **`libfprint`**.

Fix: GitHub commit `c74771d761834c87a64948060bda44415b42dbc3` corrects exactly three handler-domain strings (one set and two remove) in the standalone diagnostic source. It does not alter the driver, matcher, retry semantics, IPC protocol or matching thresholds.

**Validation status:** functional quality-recovery behaviour observed; patched counter has not yet been rerun on the user's hardware. A subsequent run of the test client is needed to observe its strict all-PASS outcome. Because enrolled prints remain RAM-only, restarting the client means repeating twelve accepted enrolment touches. Re-enrolment is not needed to establish the existing observed driver retry+MATCH outcome.

Before proceeding to any system-wide fprintd/PAM installation, independently review runtime privilege boundaries and test an isolated fprintd instance. In particular, the test-only gateway proxy runs outside the DLL sandbox and must not be promoted to any production configuration.
