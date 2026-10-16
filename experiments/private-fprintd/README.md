# Private fprintd enrolment / verification (FT5955 v0.9.6)

**Status (16 October 2026): physical enrolment and one fresh `verify-match` through private `fprintd` PASSED on Nobara.** The updated `/dev/tty` confirmation client was used; one `enroll-retry-scan` was handled before successful enrolment. Further genuine/impostor and persistence tests are still required. Source and documentation are versioned on a separate GitHub branch. The previous **v0.9.5** experiment confirmed that a private `fprintd` process can enumerate and Claim the FocalTech 2808:5955 reader; it did not enrol or verify a finger.

## Scope

- `ft5955_private_polkit_v095.c` — unchanged protocol logic from the successful local private-bus authorisation prototype; allows only the fingerprint `enroll` and `verify` actions, only to the local user on a disposable bus.
- `ft5955_private_enroll_v096.c` — one persistent GDBus connection from Claim through EnrollStart/EnrollStatus/EnrollStop, VerifyStart/VerifyStatus/VerifyStop and Release.
- `ft5955_private_enroll_v096.sh` — compile-only option plus private-bus launcher. Starts local unmodified `/usr/libexec/fprintd`, injects only the experimental built libfprint, sets `STATE_DIRECTORY` to `/dev/shm`, and cleans up.

The script is **specific to the user's Nobara development checkout** and expects:
- `~/Projects/libfprint-ft5955/build-ft5955/libfprint/libfprint-2.so.2`
- `~/Projects/ft5955-driver-integration-v0.8/engine/engine_gateway.py`
- `/usr/libexec/fprintd`
- `cc`, `pkg-config`, GLib/GIO development headers, `dbus-run-session`, `gdbus`, `findmnt`, `timeout`, `mktemp`.

The libfprint driver and gateway **remain local experimental work**; this GitHub branch does not contain a reproducible full Linux driver build. An independent clone of this repository alone is not enough for the live test.

## Download via Git (no archive needed)

**Simplest on the existing Nobara setup — do not create another project directory.**
Fetch the two new files from GitHub into the existing validation tests folder. The
successful v0.9.5 `ft5955_private_polkit_v095.c` is **already there** and will
not be overwritten.

```bash
bash <<'BASH'
set -euo pipefail
REPO="$HOME/Projects/focaltech-5955-linux"
TESTS="$HOME/Projects/ft5955-native-validation-v0.9.1/tests"
BRANCH="origin/feature/ft5955-private-fprintd-v096"

git -C "$REPO" fetch origin feature/ft5955-private-fprintd-v096

for name in ft5955_private_enroll_v096.c ft5955_private_enroll_v096.sh; do
    destination="$TESTS/$name"
    if [[ -e "$destination" ]]; then
        echo "STOP: file already exists: $destination"
        exit 2
    fi
    git -C "$REPO" show "$BRANCH:experiments/private-fprintd/$name" > "$destination"
done

bash "$TESTS/ft5955_private_enroll_v096.sh" --check
BASH
```

This does **not** check out or merge another branch into your existing Git working tree. It
leaves all uncommitted driver changes alone. If `--check` fails, **stop there** and
report the compiler error.

**Alternative:** for independent review of the complete GitHub branch without
copying individual files, use a separate detachable Git worktree:

From the existing local Git checkout:

```bash
cd ~/Projects/focaltech-5955-linux
git fetch origin feature/ft5955-private-fprintd-v096
git show origin/feature/ft5955-private-fprintd-v096:experiments/private-fprintd/ft5955_private_enroll_v096.sh > /tmp/ft5955_private_enroll_v096.sh
```

To run the entire test from Git **without disturbing the current checkout or uncommitted changes**, use a separate worktree (path must not already exist):

```bash
cd ~/Projects/focaltech-5955-linux
git fetch origin feature/ft5955-private-fprintd-v096
git worktree add --detach ../ft5955-v096-github-test origin/feature/ft5955-private-fprintd-v096
bash ../ft5955-v096-github-test/experiments/private-fprintd/ft5955_private_enroll_v096.sh --check
```

`--check` **only compiles** both C programmes; there are **no live fingerprint scans or authentication changes**. The user's Nobara run on **16 October 2026** printed `PASS: test programmes compiled. No fingerprint scanned.` The first live attempt was blocked by USB permissions; a subsequent run after a per-device ACL grant completed enrolment but ended at the stdin EOF prompt. A later corrected `/dev/tty` run **completed enrolment and returned a fresh `verify-match`**.

Only after a successful check and review of the code:

```bash
bash ~/Projects/ft5955-v096-github-test/experiments/private-fprintd/ft5955_private_enroll_v096.sh --live
```

The live test explicitly asks for **one right-index finger**, expects 12 accepted impressions, then requires lifting the finger and pressing Enter before verifying. It regards `NO_MATCH`, timeout, D-Bus method errors and incomplete enrolment as failure. **Most recent `--live` run passed Claim, enrolment and a fresh `VerifyStatus: verify-match (done=true)`. The test remains experimental and is not enabled for Linux login.**

## Next test: update existing C client

Because v0.9.6 files already exist in the local validation tests directory, fetch
the corrected C client rather than creating another folder or re-running the
initial two-file download (which refuses existing files).

```bash
git -C ~/Projects/focaltech-5955-linux fetch origin feature/ft5955-private-fprintd-v096
git -C ~/Projects/focaltech-5955-linux show origin/feature/ft5955-private-fprintd-v096:experiments/private-fprintd/ft5955_private_enroll_v096.c > ~/Projects/ft5955-native-validation-v0.9.1/tests/ft5955_private_enroll_v096.c
bash ~/Projects/ft5955-native-validation-v0.9.1/tests/ft5955_private_enroll_v096.sh --check
```

Then run `bash ~/Projects/ft5955-native-validation-v0.9.1/tests/ft5955_private_enroll_v096.sh --live` directly in a terminal, without `sudo`.
This will **enrol the finger again** because temporary test storage is deleted after
each session. The fixed confirmation prompt uses `/dev/tty` rather than stdin,
avoiding the EOF caused by launching from a heredoc.

## Multi-finger positive and negative controls (new; not yet hardware-tested)

The same existing v0.9.6 test client and launcher now provide `--controls`:

```bash
bash ~/Projects/ft5955-native-validation-v0.9.1/tests/ft5955_private_enroll_v096.sh --controls
```

**Update BOTH files from the existing GitHub feature branch first**: `ft5955_private_enroll_v096.c` **and** `ft5955_private_enroll_v096.sh`. The existing `--check` still compiles both programmes without touching the sensor. Previous `--live` behaviour is preserved.

The controls enrol the **right index finger only once** and then perform four separate comparisons on the same held open D-Bus connection and the same disposable private state:

1. **Right index** (enrolled) — expected `verify-match`.
2. **Right middle** (unenrolled) — expected `verify-no-match`.
3. **Left index** (unenrolled) — expected `verify-no-match`.
4. **Right index again** — expected `verify-match`.

The `VerifyStart` argument remains `right-index-finger` for all four checks because that is the **enrolled template**; physically touch the actual finger stated by the prompt, not an alternative print slot. The programme waits for a fresh Enter after the sensor is clear before **each** new verification. Keep the sensor untouched until `Verification started` appears. Quality retries are **not** counted as a negative rejection or success. Only a terminal `verify-no-match` qualifies as a successful negative control; any unexpected positive match, negative mismatch, timeout, error, or incomplete enrolment stops the test. This remains one small experiment, not a false-accept-rate measurement.

All operations run in the existing private test stack, with the original temporary RAM-backed storage cleanup and **no PAM/KDE/system fprintd changes**. Non-root USB read/write permission is still required (the earlier device-specific ACL may reset after a reconnect). Never run the launcher with `sudo`.

## Confirmed physical result — 16 October 2026

The updated C client ran against the real `2808:5955` fingerprint reader on Nobara using a disposable private `fprintd` bus and RAM-backed state directory:

- Device enumerated; non-root `Claim` succeeded with temporary per-device ACL permission.
- Enrolment returned 11 intermediate `enroll-stage-passed` notifications, **one recoverable `enroll-retry-scan`** and finally `enroll-completed (done=true)`.
- With the finger lifted and a new verification started by Enter, `VerifyStatus` returned **`verify-match (done=true)`**.
- Both enrolment and verification received private PolicyKit authorisation; the private state directory/logs were removed at exit.

**One verified fresh genuine match has been demonstrated through fprintd; the new multi-finger controls are still pending a Nobara run.** Tests of different fingers (negative controls), repeated matches, separate sessions, template reload and production PAM/KDE integration have not yet been completed. Historical earlier failure diagnoses below are retained for context, not current blockers.

## Safety and cleanup

- **Do not use sudo** and do not run against the real system bus.
- No changes to system PAM, KDE, udev rules, default systemd services or `/var/lib/fprint`.
- Fingerprint storage is redirected for the private fprintd process through `STATE_DIRECTORY` under a unique `/dev/shm/ft5955-v096.*` directory. It is deleted on normal exit. Sudden termination could leave RAM-backed files until cleaned up or rebooted; never copy or upload them.
- The D-Bus client prints *status signals*, not fingerprint images/templates. Treat error logs and any locally stored biometric material as sensitive.
- Device-resident storage, if ever supported by a future driver, requires separate review; this isolation is a host-storage test arrangement.
- Existing native v0.9.4 tests remain available separately. A successful RAM-only native comparison does not imply that `fprintd` has saved or verified a print.

## Pass criteria

1. Private PolicyKit and fprintd start successfully.
2. Device enumerates and Claim succeeds on one persistent D-Bus connection.
3. `EnrollStatus` reaches `enroll-completed`; rejected stages are retried rather than counted as accepted.
4. After deliberate lift and new touch, `VerifyStatus` returns `verify-match`.
5. Release succeeds and the private process/storage is cleaned up.

This is **not** approval for enabling login/PAM. Next steps require several fresh genuine/impostor trials, repeatability checks, template storage review and documentation of known failures.

See [project status, 16 October 2026](../../docs/status-2026-10-16.md).

## Historical troubleshooting: earlier USB permission failure (resolved temporarily)

The private fprintd enumerated the device and obtained an `ALLOW` response for `net.reactivated.fprint.device.verify`, but the driver could not open its physical USB device node. The log included `libusb requires write access to USB device nodes`, `errno=13` and `LIBUSB_ERROR_ACCESS [-3]`. This occurred **before** `EnrollStart`; no biometric data was captured. The missing private-bus `login1` service and USB-persist warning were not the immediate cause.

Next: read-only inspection of `/sys/bus/usb/devices/*/{idVendor,idProduct,busnum,devnum}`, the resulting `/dev/bus/usb/BBB/DDD` node, `stat`, `getfacl`, and `udevadm info`; do not assume the previous numeric path survives replug/reboot. Avoid `chmod 666` or launching the private PolicyKit test as root. A narrowly scoped USB permission arrangement can be considered after inspecting ACL/udev state. 

### Confirmed USB permissions and proposed non-root test

On 16 October the local device `/dev/bus/usb/003/003` was `root:root crw-rw-r--` with no user ACL: the current user could **read** but could not **write**. SELinux was disabled. This explains the libusb `errno=13` at `Claim`; it is independent of private PolicyKit's `ALLOW` decision.

For a single test, only after checking that the device node **still belongs to VID:PID 2808:5955**, one may grant the existing user a *temporary, per-device* ACL:

```bash
DEVICE=/dev/bus/usb/003/003
udevadm info --query=property --name="$DEVICE" | grep -E '^ID_(VENDOR|MODEL)_ID='
sudo setfacl -m "u:$(id -un):rw" "$DEVICE"
getfacl -p "$DEVICE"
```

This is **not** a permanent fix: the numeric node and ACL may change on replug/reboot. Do not execute if the USB IDs do not match, do not use `sudo` to run the private fprintd harness, and do not apply `chmod 666` or global USB rules. A dedicated udev `TAG+="uaccess"` rule can be investigated only once the live test works with a narrow ACL. Temporary device-specific ACL was subsequently tested and permitted successful enrolment plus a fresh verification match. It is not a permanent udev solution.
