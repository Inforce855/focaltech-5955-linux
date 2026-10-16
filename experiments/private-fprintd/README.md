# Private fprintd enrolment / verification (FT5955 v0.9.6)

**Status (16 October 2026): physical fprintd enrolment PASSED after granting per-device USB write permission. Verification did not begin because the first completed enrolment was launched through a heredoc and the old client read EOF from stdin. GitHub now has a `/dev/tty` confirmation fix, pending a Nobara test.** Source and documentation are versioned on a separate GitHub branch. The previous **v0.9.5** experiment confirmed that a private `fprintd` process can enumerate and Claim the FocalTech 2808:5955 reader; it did not enrol or verify a finger.

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

`--check` **only compiles** both C programmes; there are **no live fingerprint scans or authentication changes**. The user's Nobara run on **16 October 2026** printed `PASS: test programmes compiled. No fingerprint scanned.` The first live attempt was blocked by USB permissions. A subsequent run after a per-device ACL grant successfully completed enrolment; fresh verification has not yet been attempted.

Only after a successful check and review of the code:

```bash
bash ~/Projects/ft5955-v096-github-test/experiments/private-fprintd/ft5955_private_enroll_v096.sh --live
```

The live test explicitly asks for **one right-index finger**, expects 12 accepted impressions, then requires lifting the finger and pressing Enter before verifying. It regards `NO_MATCH`, timeout, D-Bus method errors and incomplete enrolment as failure. **Latest `--live` run passed Claim and enrolment. Fresh verification is pending: fetch the updated C client before retesting.**

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

## 16 October 2026 — first live result and next diagnostic

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

This is **not** a permanent fix: the numeric node and ACL may change on replug/reboot. Do not execute if the USB IDs do not match, do not use `sudo` to run the private fprintd harness, and do not apply `chmod 666` or global USB rules. A dedicated udev `TAG+="uaccess"` rule can be investigated only once the live test works with a narrow ACL. Proposed workaround currently **untested**.
