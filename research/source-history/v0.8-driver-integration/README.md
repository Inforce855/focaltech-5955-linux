# FT5955 native libfprint driver integration v0.8 — experimental source patch

**User-supplied source snapshot:** 14 October 2026, from
`~/Projects/libfprint-ft5955`, `libfprint/drivers/focaltech_5955.c`
(5545 bytes) and `libfprint/meson.build` (11280 bytes).

## What is implemented

This is the **first integrated native libfprint driver source**, not a mock
protocol adapter. `apply.py` preserves the supplied descriptor/handshake,
claim/release and one-time finger-status code *byte-for-byte in its original
sections* and adds native enrolment and verification vfuncs and seven
source files to the same private build.

- Asynchronous libfprint `FpDevice` `enroll` / `verify` vfuncs on a `GTask`
  worker, with libfprint progress, retries, final match/no-match callbacks
  delivered back on the main context.
- USB status (`0x82`) enforces an observed **release then new press** for every
  impression. Validated readiness (`0x80`) and image (`0x81`) packets follow;
  no unverified `0x87` command, USB reset, power mode or persistence changes.
- Bounded, validated `10240`-byte raw acquisition and the previously tested
  **little-endian 16-bit → 1st/99th percentile stretch → invert** conversion
  to a 5120-byte MOH engine frame.
- External supervisor gateway invokes the audited SHA-pinned vendor DLL runner
  inside `bubblewrap` with NO USB/network access inside the sandbox.
- Existing 12-accepted-impression state machine, bounded retries, versioned
  MOH template codec, `FPI_PRINT_RAW` assignment and verify import.
- Opt-in environment gate: the driver cannot perform biometric operations
  unless `FT5955_EXPERIMENTAL_ENABLE=1` and `FT5955_ENGINE_GATEWAY` points to
  this package's `engine/engine_gateway.py`.

**Not yet proven:** native driver compilation in the user's 1.94.100 build,
USB sample acceptance from native GUsb transfers, full FpPrint roundtrip via
these driver callbacks, cancellation/unplug safety under hardware conditions,
secure persistent storage or fprintd/PAM login. Do **not** install this patch
into the system libfprint or use it for authentication. The vendor DLL is still
proprietary and the matcher's security is unassessed.

## Offline verification (no USB, sudo or vendor DLL)

```bash
cd ~/Projects/ft5955-driver-integration-v0.8
bash run_source_checks.sh
python3 apply.py --check
```

The patch refuses if either of the two exact input files has changed, if the
expected insertion points differ, if backup files already exist, or if any
added source name already exists in the target checkout.

## Apply to isolated *development checkout* ONLY

```bash
cd ~/Projects/ft5955-driver-integration-v0.8
python3 apply.py --apply
cd ~/Projects/libfprint-ft5955
ninja -C build-ft5955
```

`ninja` may trigger Meson regeneration. The v0.8 code has not yet been compiled
against your private Nobara headers; **report compile diagnostics rather than
installing or proceeding to login**. No source from your MOH feature-branch
worktree is modified. No package files or biometrics are written to GitHub.

Build a standalone public-API integration probe **after the private build
succeeds**, without capturing fingerprints:

```bash
cd ~/Projects/ft5955-driver-integration-v0.8
bash build_private_test.sh
```

## Optional deliberately authorised real test — NOT YET RECOMMENDED

Only after the native build and test client both compile, with a normal user
and the device not in use by system fprintd, can this experimental driver be
exercised under private libfprint:

```bash
cd ~/Projects/ft5955-driver-integration-v0.8
export FT5955_EXPERIMENTAL_ENABLE=1
export FT5955_ENGINE_GATEWAY="$PWD/engine/engine_gateway.py"
./build-tests/native_enroll_verify --live
```

The probe only retains one versioned FpPrint in process RAM, enrolls 12
accepted impressions and verifies one fresh scan; it does not save data.
A fresh MOH sandbox is created per libfprint operation. The first real
integration test must be supervised, and stops on errors.

## Restore driver/meson

```bash
cd ~/Projects/ft5955-driver-integration-v0.8
python3 restore.py --restore
```

The restore script copies back byte-for-byte backups of your *original* two
files. New `libfprint/drivers/ft5955_*` files remain to avoid deleting
potential subsequent work. Review `git diff` and `git status` before cleanup.

**Risk boundaries:** Print envelope SHA-256 is an error detector, not
encryption. The process memory still contains fingerprint data and vendor
features until cleared/freed; the GLib `GVariant` storage is not protected
against process-memory copying or crash dumps. Do not save serialized prints
unprotected. `fprintd` support is a separate later stage.
