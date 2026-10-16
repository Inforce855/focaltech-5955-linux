#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# FT5955 v0.9.6: disposable private D-Bus fprintd enrol/verify test.
# No system PolicyKit, system fprintd, PAM, udev or /var/lib/fprint changes.
set -euo pipefail
umask 077

if [[ $# -ne 1 || ( "${1:-}" != "--check" && "${1:-}" != "--live" && "${1:-}" != "--controls" && "${1:-}" != "--diagnose" && "${1:-}" != "--roundtrip" ) ]]; then
    echo "Usage: $0 --check | --live | --controls | --diagnose | --roundtrip" >&2
    exit 2
fi
if [[ $EUID -eq 0 ]]; then
    echo "STOP: never run as root." >&2
    exit 2
fi
for utility in cc pkg-config dbus-run-session gdbus findmnt timeout mktemp; do
    command -v "$utility" >/dev/null || {
        echo "STOP: missing $utility" >&2
        exit 2
    }
done
pkg-config --exists gio-2.0 glib-2.0 || {
    echo "STOP: gio-2.0 and glib-2.0 development headers are required." >&2
    exit 2
}
[[ "$(findmnt -n -o FSTYPE -T /dev/shm)" == "tmpfs" ]] || {
    echo "STOP: /dev/shm must be tmpfs." >&2
    exit 2
}

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_SOURCE="$HERE/ft5955_private_enroll_v096.c"
POLKIT_SOURCE="$HERE/ft5955_private_polkit_v095.c"
LIB="${FT5955_PRIVATE_LIB_DIR:-$HOME/Projects/libfprint-ft5955/build-ft5955/libfprint}"
GATEWAY="${FT5955_PRIVATE_GATEWAY:-$HOME/Projects/ft5955-driver-integration-v0.8/engine/engine_gateway.py}"

[[ -f "$CLIENT_SOURCE" && -f "$POLKIT_SOURCE" ]] || {
    echo "STOP: missing companion C sources." >&2
    exit 2
}
[[ -f "$LIB/libfprint-2.so.2" && -f "$GATEWAY" ]] || {
    echo "STOP: private libfprint or experimental gateway is missing." >&2
    exit 2
}
[[ -x /usr/libexec/fprintd ]] || {
    echo "STOP: Nobara's /usr/libexec/fprintd is missing." >&2
    exit 2
}

BUILD="$(mktemp -d /tmp/ft5955-v096-build.XXXXXX)"
cleanup_build() {
    [[ ! -d "$BUILD" ]] || rm -rf -- "$BUILD"
}
trap cleanup_build EXIT

# shellcheck disable=SC2046
cc -std=gnu11 -O2 -Wall -Wextra -Werror \
    $(pkg-config --cflags gio-2.0 glib-2.0) "$POLKIT_SOURCE" \
    $(pkg-config --libs gio-2.0 glib-2.0) -o "$BUILD/private_polkit"

# shellcheck disable=SC2046
cc -std=gnu11 -O2 -Wall -Wextra -Werror \
    $(pkg-config --cflags gio-2.0 glib-2.0) "$CLIENT_SOURCE" \
    $(pkg-config --libs gio-2.0 glib-2.0) -o "$BUILD/private_enroll"

if [[ "$1" == "--check" ]]; then
    echo "PASS: test programmes compiled. No fingerprint scanned."
    exit 0
fi

export FT5955_V096_PRIVATE_CLIENT="$BUILD/private_enroll"
export FT5955_V096_PRIVATE_MODE="$1"
export FT5955_V096_PRIVATE_POLICY="$BUILD/private_polkit"
export FT5955_V096_PRIVATE_LIB="$LIB"
export FT5955_V096_PRIVATE_GATEWAY="$GATEWAY"

dbus-run-session -- bash -c '
    set -euo pipefail
    umask 077
    [[ $EUID -ne 0 && -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]] || exit 2

    # Redirect the system-bus API ONLY for subprocesses inside this
    # disposable dbus-run-session; normal desktop processes are unaffected.
    export DBUS_SYSTEM_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS"
    export FT5955_TEST_PRIVATE_POLKIT=1
    export FT5955_V096_PRIVATE_ENROLL=1
    export FT5955_EXPERIMENTAL_ENABLE=1
    export FT5955_ENGINE_GATEWAY="$FT5955_V096_PRIVATE_GATEWAY"
    export LD_LIBRARY_PATH="$FT5955_V096_PRIVATE_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

    TEST_DIR="$(mktemp -d /dev/shm/ft5955-v096.XXXXXX)"
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
        if [[ "$TEST_DIR" == /dev/shm/ft5955-v096.* && -d "$TEST_DIR" ]]; then
            rm -rf -- "$TEST_DIR"
        fi
    }
    trap cleanup EXIT

    "$FT5955_V096_PRIVATE_POLICY" >"$TEST_DIR/polkit.log" 2>&1 &
    policy_pid=$!
    ready=false
    for _ in {1..50}; do
        if [[ "$(timeout 2s gdbus call --address "$DBUS_SYSTEM_BUS_ADDRESS" \
                --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
                --method org.freedesktop.DBus.NameHasOwner \
                org.freedesktop.PolicyKit1 2>/dev/null || true)" == "(true,)" ]]; then
            ready=true
            break
        fi
        sleep 0.1
    done
    if [[ "$ready" != true ]]; then
        echo "FAIL: private PolicyKit did not start." >&2
        cat "$TEST_DIR/polkit.log" >&2
        exit 4
    fi

    launch_fprintd() {
        local log_file="$1"
        local ready=false
        /usr/libexec/fprintd >"$log_file" 2>&1 &
        fp_pid=$!
        for _ in {1..50}; do
            if [[ "$(timeout 2s gdbus call --address "$DBUS_SYSTEM_BUS_ADDRESS" \
                    --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
                    --method org.freedesktop.DBus.NameHasOwner \
                    net.reactivated.Fprint 2>/dev/null || true)" == "(true,)" ]]; then
                ready=true
                break
            fi
            if ! kill -0 "$fp_pid" 2>/dev/null; then
                break
            fi
            sleep 0.2
        done
        if [[ "$ready" != true ]]; then
            echo "FAIL: private fprintd did not acquire its D-Bus name." >&2
            tail -n 35 "$log_file" >&2
            return 5
        fi
    }

    launch_fprintd "$TEST_DIR/fprintd.log" || exit 5

    echo "Private fprintd ready. Storage is on disposable /dev/shm."
    echo "Use the SAME right index finger for all enrolment touches."
    status=0
    if [[ "$FT5955_V096_PRIVATE_MODE" == "--roundtrip" ]]; then
        echo "PHASE 1: Enrol once and confirm fprintd lists the finger."
        "$FT5955_V096_PRIVATE_CLIENT" --enroll-only || status=$?
        if [[ $status -eq 0 ]]; then
            echo "Restarting ONLY private fprintd; retaining disposable RAM storage."
            kill "$fp_pid" 2>/dev/null || true
            wait "$fp_pid" 2>/dev/null || true
            fp_pid=""
            if launch_fprintd "$TEST_DIR/fprintd-restarted.log"; then
                echo "PHASE 2: New fprintd process, new client, same RAM storage."
                "$FT5955_V096_PRIVATE_CLIENT" --verify-saved || status=$?
            else
                status=5
            fi
        fi
        if [[ $status -eq 0 ]]; then
            echo "PASS: enrolment survived a private daemon restart."
        else
            echo "FAIL: cross-daemon saved-template roundtrip." >&2
        fi
    else
        "$FT5955_V096_PRIVATE_CLIENT" "$FT5955_V096_PRIVATE_MODE" || status=$?
    fi

    echo "=== PRIVATE POLICYKIT RESULTS ==="
    grep "PRIVATE BUS TEST PolicyKit:" "$TEST_DIR/polkit.log" || true
    if [[ $status -ne 0 ]]; then
        echo "=== PRIVATE FPRINTD DIAGNOSTICS ==="
        grep -Ei "error|warning|failed|focaltech|ft5955" \
            "$TEST_DIR/fprintd.log" | tail -n 35 || true
        if [[ -f "$TEST_DIR/fprintd-restarted.log" ]]; then
            echo "=== PRIVATE RESTARTED FPRINTD DIAGNOSTICS ==="
            grep -Ei "error|warning|failed|focaltech|ft5955" \
                "$TEST_DIR/fprintd-restarted.log" | tail -n 35 || true
        fi
    fi
    echo "Removing disposable template directory and logs."
    exit "$status"
'
