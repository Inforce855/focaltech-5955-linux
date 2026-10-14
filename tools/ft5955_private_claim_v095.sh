#!/usr/bin/env bash
# FT5955 v0.9.5: private-bus Claim-only test (NO enrolment).
# No system PolicyKit, service units, /var/lib/fprint or PAM changes.
set -euo pipefail

if [[ $EUID -eq 0 ]]; then
  echo "STOP: do not run as root." >&2; exit 2
fi
for util in cc pkg-config dbus-run-session gdbus timeout; do command -v "$util" >/dev/null; done
pkg-config --exists gio-2.0 glib-2.0

source_dir="$(cd "$(dirname "$0")" && pwd)"
source_file="$source_dir/ft5955_private_polkit_v095.c"
private_lib="$HOME/Projects/libfprint-ft5955/build-ft5955/libfprint"
[[ -f "$source_file" && -f "$private_lib/libfprint-2.so.2" ]] || {
  echo "STOP: missing private test source or private libfprint." >&2; exit 2
}
[[ -f "$HOME/Projects/ft5955-driver-integration-v0.8/engine/engine_gateway.py" ]] || {
  echo "STOP: expected private gateway is missing." >&2; exit 2
}

build_dir="$(mktemp -d /tmp/ft5955-claim-build.XXXXXX)"
cleanup_build() { [[ -n "$build_dir" && -d "$build_dir" ]] && rm -rf -- "$build_dir"; }
trap cleanup_build EXIT

# shellcheck disable=SC2046
cc -std=gnu11 -O2 -Wall -Wextra -Werror \
  $(pkg-config --cflags gio-2.0 glib-2.0) "$source_file" \
  $(pkg-config --libs gio-2.0 glib-2.0) \
  -o "$build_dir/private_polkit_test"

export FT5955_V095_TEST_HELPER="$build_dir/private_polkit_test"
export FT5955_V095_PRIVATE_LIB="$private_lib"

dbus-run-session -- bash -c '
  set -euo pipefail
  [[ $EUID -ne 0 ]]
  [[ -n "$DBUS_SESSION_BUS_ADDRESS" ]]

  # Both services see ONLY the new dbus-run-session bus.
  export DBUS_SYSTEM_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS"
  export FT5955_TEST_PRIVATE_POLKIT=1
  export LD_LIBRARY_PATH="$FT5955_V095_PRIVATE_LIB"
  export FT5955_EXPERIMENTAL_ENABLE=1
  export FT5955_ENGINE_GATEWAY="$HOME/Projects/ft5955-driver-integration-v0.8/engine/engine_gateway.py"
  TEST_DIR="$(mktemp -d /tmp/ft5955-claim-private.XXXXXX)"
  export STATE_DIRECTORY="$TEST_DIR"
  policy_pid=""
  fp_pid=""
  cleanup() {
    if [[ -n "$fp_pid" ]]; then
      kill "$fp_pid" 2>/dev/null || true
      wait "$fp_pid" 2>/dev/null || true
    fi
    if [[ -n "$policy_pid" ]]; then
      kill "$policy_pid" 2>/dev/null || true
      wait "$policy_pid" 2>/dev/null || true
    fi
    [[ -n "$TEST_DIR" && -d "$TEST_DIR" ]] && rm -rf -- "$TEST_DIR"
  }
  trap cleanup EXIT

  "$FT5955_V095_TEST_HELPER" >"$TEST_DIR/test-policy.log" 2>&1 &
  policy_pid=$!
  ready=false
  for _ in {1..30}; do
    if [[ "$(gdbus call --address "$DBUS_SYSTEM_BUS_ADDRESS" \
          --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
          --method org.freedesktop.DBus.NameHasOwner \
          org.freedesktop.PolicyKit1 2>/dev/null || true)" == "(true,)" ]]; then
      ready=true; break
    fi
    sleep 0.1
  done
  if [[ "$ready" != true ]]; then
    echo "FAIL: private test PolicyKit stub did not acquire its name." >&2
    cat "$TEST_DIR/test-policy.log"
    exit 4
  fi

  /usr/libexec/fprintd >"$TEST_DIR/fprintd.log" 2>&1 &
  fp_pid=$!

  # D-Bus does not activate the manually started daemon: wait until its
  # well-known name has been acquired. An immediate GetDevices races startup.
  fp_ready=false
  for _ in {1..50}; do
    if [[ "$(timeout 2s gdbus call --address "$DBUS_SYSTEM_BUS_ADDRESS" \
          --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
          --method org.freedesktop.DBus.NameHasOwner \
          net.reactivated.Fprint 2>/dev/null || true)" == "(true,)" ]]; then
      fp_ready=true; break
    fi
    if ! kill -0 "$fp_pid" 2>/dev/null; then
      echo "FAIL: private fprintd exited before registering its D-Bus name." >&2
      break
    fi
    sleep 0.2
  done
  if [[ "$fp_ready" != true ]]; then
    echo "FAIL: private fprintd was not ready; not attempting Claim." >&2
    echo "=== Private PolicyKit log ==="
    cat "$TEST_DIR/test-policy.log"
    echo "=== Private fprintd log ==="
    cat "$TEST_DIR/fprintd.log"
    exit 5
  fi

  echo "=== Private fprintd device enumeration ==="
  enumerate_rc=0
  timeout 15s gdbus call --address "$DBUS_SYSTEM_BUS_ADDRESS" \
    --dest net.reactivated.Fprint \
    --object-path /net/reactivated/Fprint/Manager \
    --method net.reactivated.Fprint.Manager.GetDevices || enumerate_rc=$?
  if [[ "$enumerate_rc" -ne 0 ]]; then
    echo "FAIL: private GetDevices call failed." >&2
    cat "$TEST_DIR/test-policy.log"
    cat "$TEST_DIR/fprintd.log"
    exit "$enumerate_rc"
  fi

  echo "=== PRIVATE BUS Claim for current user (no fingerprint capture) ==="
  claim_rc=0
  timeout 15s gdbus call --address "$DBUS_SYSTEM_BUS_ADDRESS" \
    --dest net.reactivated.Fprint \
    --object-path /net/reactivated/Fprint/Device/0 \
    --method net.reactivated.Fprint.Device.Claim "" || claim_rc=$?

  echo "=== Private PolicyKit test decisions ==="
  cat "$TEST_DIR/test-policy.log"
  echo "=== Private fprintd log ==="
  cat "$TEST_DIR/fprintd.log"

  if [[ "$claim_rc" -ne 0 ]]; then
    echo "FAIL: Claim did not succeed. Temporary services will be removed." >&2
    exit "$claim_rc"
  fi
  echo "PASS: isolated fprintd Claim succeeded without modifying system PolicyKit."
  echo "No fingerprint enrolled. Private state directory will be deleted."
'
