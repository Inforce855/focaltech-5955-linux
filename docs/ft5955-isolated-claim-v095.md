# FT5955 v0.9.5: isolated fprintd Claim test (14 October 2026)

The user's first Claim attempt returned PermissionDenied because the disposable D-Bus lacks the service org.freedesktop.PolicyKit1. This is expected and does not indicate a fault in the FT5955 driver. The private fprintd previously enumerated the device and returned its correct properties.

Two new reviewed source files are in tools/:

- ft5955_private_polkit_v095.c: a test-only PolicyKit protocol stub on the private bus. It allows only enroll and verify actions for same-UID subjects and callers. It denies setusername and unrelated actions. It refuses root, requires explicit opt-in and requires redirected system bus address equal to its private session bus address.
- ft5955_private_claim_v095.sh: compile the stub against GIO/GLib in /tmp, start a disposable dbus-run-session bus, redirect fprintd to private libfprint and a temporary STATE_DIRECTORY, test GetDevices followed by Claim for the current user, print logs and clean up. It does NOT enrol or store biometric templates.

Important: This stub is NOT real PolicyKit and does not test the security properties of actual PolicyKit. Do not launch on the real system bus, install the program, run as root, copy it to a privileged daemon, or use it in a production login configuration. No real fprintd service, packages, /var/lib/fprint or PAM files are modified.

## Retrieve source files without changing Git worktrees

~~~bash
(
  set -e
  cd ~/Projects/focaltech-5955-moh-test
  git fetch origin feature/ft5955-moh-engine-bridge
  TARGET="$HOME/Projects/ft5955-native-validation-v0.9.1/tests"
  test -d "$TARGET"
  test ! -e "$TARGET/ft5955_private_polkit_v095.c"
  test ! -e "$TARGET/ft5955_private_claim_v095.sh"
  git show FETCH_HEAD:tools/ft5955_private_polkit_v095.c > "$TARGET/ft5955_private_polkit_v095.c"
  git show FETCH_HEAD:tools/ft5955_private_claim_v095.sh > "$TARGET/ft5955_private_claim_v095.sh"
  bash -n "$TARGET/ft5955_private_claim_v095.sh"
)
~~~

Inspect both new source files before running. Run without sudo:

~~~bash
bash ~/Projects/ft5955-native-validation-v0.9.1/tests/ft5955_private_claim_v095.sh
~~~

Expected: a device object path from GetDevices and a successful Claim result (normally the empty tuple), with log entries from the private test policy helper. Failures must be investigated from the output: compilation and live Claim have not yet been tested on Nobara. The one-off gdbus Claim client disconnects after the call; longer enrol/verification tests will require a persistent connection and independent checking of private template storage.

No enrolment and no login authentication are attempted by this v0.9.5 script.