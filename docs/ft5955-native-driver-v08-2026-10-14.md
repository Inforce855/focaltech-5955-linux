# FT5955 native libfprint driver integration v0.8 — 14 October 2026

**Status: development source patch, awaiting compilation against user's isolated Nobara libfprint tree. No fprintd/PAM/system installation.**

The user's two actual local source files were supplied: `libfprint/drivers/focaltech_5955.c` (5,545 bytes) and `libfprint/meson.build` (11,280 bytes). The original USB descriptor, open/close, claim/release, audited handshake `0x34`, and first status `0x82` logic were preserved.

A separate standalone source bundle `ft5955-driver-integration-v0.8.tar.gz` has been created with an exact-file-hash, reversible patch (`apply.py --check`, `--apply`, `restore.py --restore`). It appends asynchronous `FpDevice.enroll` / `FpDevice.verify` vfuncs, GLib worker acquisition with audited status/readiness/image commands, 64x80 inverted contrast-processed frame conversion, versioned `FPI_PRINT_RAW` MOH template and isolated engine gateway using the existing pinned-DLL `bubblewrap` runner. Two environment opt-ins (`FT5955_EXPERIMENTAL_ENABLE=1` and explicit absolute `FT5955_ENGINE_GATEWAY`) prevent accidental use. The source remains proprietary-matcher-backed, not a fully open-source algorithm.

**Local development checks passed:** C action-state regression (12 accepted stages, retries, verify, cancellation), four synthetic codec tests (including C/Python compatibility), two engine-gateway synthetic protocol tests, Python syntax, and applying/restoring the source patch on a temporary copy of the exact uploaded files. Real compilation against the user's private libfprint 1.94.100 headers/runtime **has not yet occurred**. Native live USB enrolment, verification, cancellation/unplug stress, serialization through actual device operations and persistent fprintd integration **must not be called complete**.

The earlier v0.6.1 `FpPrint` synthetic serialization harness and v0.7 callback header bridge *did* pass on the user's Nobara private build; the new combined v0.8 driver must compile and be tested separately. Do not mix those claims.

No private biometric images, user templates or proprietary DLL were uploaded or committed. The existing MOH feature worktree and running GUI remain unchanged.

## Confirmed private native driver build — 14 October 2026

The user applied the exact v0.8 source patch to `/home/tim/Projects/libfprint-ft5955` and ran `ninja -C build-ft5955` on Nobara (libfprint 1.94.100, GCC 16.2.1, gusb 0.4.9). Meson regenerated with `drivers: virtual_device,focaltech_5955` and the build **completed successfully**, including `drivers_ft5955_native_capture.c.o` and final target generation. The only visible warning was `-Wmisleading-indentation` at `libfprint/drivers/ft5955_native_capture.c:71` for two adjacent `if` statements on one line. The v0.8 offline action-state, codec and gateway tests passed, and the exact source hashes and backup/patch checks passed. The binary `native_enroll_verify` is a separate private-libfprint public-API probe, and **has not yet been compiled/run by the user**. No claim of native real-hardware enrolment or verification is warranted yet. No system installation or PAM/fprintd change was made.
