# FT5955 v0.9 — Real native FpPrint and negative-control validation

This **adds a test client only**. It neither patches the now-working native
`focaltech_5955` driver nor changes the MOH sandbox or Nobara's fprintd/PAM.

## What this tests

1. One live native-libfprint 12-accepted-impression enrolment.
2. `fp_print_serialize()` on the **real** print returned by native enrolment,
   with the serialized bytes held in memory only.
3. Release the original `FpPrint`; close the private libfprint device and
   destroy the original `FpContext`.
4. `fp_print_deserialize()` in memory; create an **entirely new** context,
   rediscover and reopen the same reader.
5. Use the restored print to verify four **operator-labelled** fresh touches:
   enrolled finger → different finger → another different finger → enrolled
   finger again. Every verify creates a fresh isolated MOH engine operation.

**Important**: This does NOT save print data to disk, demonstrate reboot
persistence, assess false-accept/reject rates, encrypt templates, or validate
PAM/fprintd. Process-memory buffers are not guaranteed to be wiped when
owned by libfprint or GLib. This is an experimental proprietary matcher.

## Build — no sudo or USB

```bash
cd ~/Projects
# Extract the supplied archive into ~/Projects first.
cd ft5955-native-validation-v0.9
bash build_private_test.sh
```

The build refuses unless `ldd` resolves `libfprint-2.so.2` into
`~/Projects/libfprint-ft5955/build-ft5955`.

## Live test — explicit opt-in, normal user only

```bash
cd ~/Projects/ft5955-native-validation-v0.9
ulimit -c 0
export FT5955_EXPERIMENTAL_ENABLE=1
export FT5955_ENGINE_GATEWAY="$HOME/Projects/ft5955-driver-integration-v0.8/engine/engine_gateway.py"
./build-tests/native_print_roundtrip --live
```

Keep all other sensor applications closed. Start each scan with the finger
**OFF** the sensor; place the requested finger only after pressing Enter. The
first and last checks use the enrolled finger. The middle checks should use
other fingers. `q` at any prompt quits without saving a template.

If either other finger returns MATCH, do not treat the setup as reliable
identification. Preserve only textual diagnostics (never biometric bytes).

The test intentionally does **not** persist templates. Do not enable a system
`fprintd` service or PAM login with this experimental build.
