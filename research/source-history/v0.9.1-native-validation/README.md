# FT5955 v0.9.1 — Native verification repeatability diagnostic

**Separate opt-in test client only.** This does not change the working v0.8 native driver, isolated vendor matcher, system libraries, fprintd, PAM, or any login settings.

The previous v0.9 live test **passed** 12-stage enrolment, real FpPrint RAM serialisation/deserialisation, reopening a new libfprint device/context, the first enrolled-finger MATCH, and two different-finger NO_MATCH results. The final enrolled-finger scan unexpectedly returned NO_MATCH. A true false rejection or user-interpretation error needs further controlled measurements; the source alone cannot attribute the cause.

This instrumented client runs one enrolment and real RAM-only FpPrint restart, followed by **10 independent, operator-labelled verification operations** against the same restored print:

- A = enrolled finger (6 tests),
- B = different finger (2 tests),
- C = another different finger (2 tests).

The order deliberately alternates A/B/A/C/A/B/A/C/A/A. All verification operations require the device to observe OFF and then a new ON; **lift completely between each**. A quality retry is printed from the public libfprint match callback, separately from a no-match decision, and counted for the final summary. No result is silently retried or reclassified into a pass. Unexpected same-finger no-match counts as a false rejection; different-finger match counts as an unexpected match. Operator cancellation mid-test exits with nonzero status; completion with unexpected results returns 8. Ten checks are a **diagnostic**, not a statistically valid fingerprint-security study.

Real biometric samples and print template remain RAM-only. There are no fingerprint/template file writes. This program never logs pixel contents, template bytes, or USB image data; GLib-owned buffers are not guaranteed to be securely zeroized.

## Compile and run on Nobara

```bash
cd ~/Projects

tar -xzf ~/Downloads/ft5955-native-validation-v0.9.1.tar.gz
cd ft5955-native-validation-v0.9.1
bash run_source_tests.sh
bash build_private_test.sh

ulimit -c 0
export FT5955_EXPERIMENTAL_ENABLE=1
export FT5955_ENGINE_GATEWAY="$HOME/Projects/ft5955-driver-integration-v0.8/engine/engine_gateway.py"
./build-tests/native_print_roundtrip --live
```

Run as an ordinary desktop user, not sudo; keep every other sensor application closed. The build checks that it links the locally built `libfprint-2.so.2`, not Nobara's system copy. If an unexpected **different-finger MATCH** occurs, do not enable authentication and keep the textual result for debugging. Do not install this experimental driver or enable system fprintd/PAM.
