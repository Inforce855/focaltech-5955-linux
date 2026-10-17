#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Isolated device Claim/Release only. No enrolment, verification or install.
set -euo pipefail
umask 077

if [[ $# -ne 1 || ( "$1" != "--check" && "$1" != "--claim-only" ) ]]; then
    echo "Usage: $0 --check | --claim-only" >&2
    exit 2
fi
if (( EUID == 0 )); then
    echo "STOP: never run as root" >&2
    exit 2
fi
for exe in cc pkg-config dbus-run-session gdbus findmnt timeout mktemp readlink; do
    command -v "$exe" >/dev/null || { echo "STOP: missing $exe" >&2; exit 2; }
done
pkg-config --exists gio-2.0 glib-2.0 || {
    echo "STOP: missing GLib/GIO development dependencies" >&2
    exit 2
}
[[ "$(findmnt -n -o FSTYPE -T /dev/shm)" == tmpfs ]] || {
    echo "STOP: /dev/shm is not tmpfs" >&2
    exit 2
}
HERE="$(cd "$(dirname "$0")" && pwd)"
CLIENT="$HERE/ft5955_claim_only_v097.c"
POLKIT="$HERE/ft5955_private_polkit_v095.c"
[[ -f "$CLIENT" && -f "$POLKIT" ]] || {
    echo "STOP: claim-only client or PolicyKit source is missing" >&2
    exit 2
}

BUILD="$(mktemp -d /tmp/ft5955-claim-client.XXXXXX)"
trap 'rm -rf -- "$BUILD"' EXIT
cc -std=gnu11 -O2 -Wall -Wextra -Werror \
    $(pkg-config --cflags gio-2.0 glib-2.0) "$CLIENT" \
    $(pkg-config --libs gio-2.0 glib-2.0) -o "$BUILD/claim_only"
cc -std=gnu11 -O2 -Wall -Wextra -Werror \
    $(pkg-config --cflags gio-2.0 glib-2.0) "$POLKIT" \
    $(pkg-config --libs gio-2.0 glib-2.0) -o "$BUILD/private_polkit"
if [[ "$1" == "--check" ]]; then
    echo "PASS: claim-only and private PolicyKit compiled; no hardware used."
    exit 0
fi

[[ -v FT5955_REBUILD_CLAIM_TEST && "$FT5955_REBUILD_CLAIM_TEST" == 1 ]] || {
    echo "STOP: use the GitHub snapshot rebuild wrapper" >&2
    exit 2
}
[[ -v FT5955_PRIVATE_LIB_DIR ]] || {
    echo "STOP: no rebuilt libfprint directory supplied" >&2
    exit 2
}
LIB="$(readlink -f -- "$FT5955_PRIVATE_LIB_DIR")"
[[ "$LIB" == /tmp/ft5955-rebuild-*/build/libfprint && -f "$LIB/libfprint-2.so.2" ]] || {
    echo "STOP: not the temporary GitHub rebuilt libfprint" >&2
    exit 2
}
SONAME="$(readlink -f -- "$LIB/libfprint-2.so.2")"
[[ -f "$SONAME" && -x /usr/libexec/fprintd ]] || {
    echo "STOP: rebuilt library or system fprintd missing" >&2
    exit 2
}
export FT5955_CLAIM_ONLY_CLIENT="$BUILD/claim_only"
export FT5955_CLAIM_ONLY_POLICY="$BUILD/private_polkit"
export FT5955_CLAIM_ONLY_SONAME="$SONAME"
export FT5955_CLAIM_ONLY_LIBDIR="$LIB"

dbus-run-session -- bash -c '
    set -euo pipefail
    umask 077
    [[ $EUID -ne 0 && -v DBUS_SESSION_BUS_ADDRESS ]] || exit 2
    # Scope system-bus remapping ONLY to our new private session.
    export DBUS_SYSTEM_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS"
    export FT5955_TEST_PRIVATE_POLKIT=1
    export FT5955_CLAIM_ONLY=1
    export LD_LIBRARY_PATH="$FT5955_CLAIM_ONLY_LIBDIR"

    TEST_DIR="$(mktemp -d /dev/shm/ft5955-claim-only.XXXXXX)"
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
        if [[ "$TEST_DIR" == /dev/shm/ft5955-claim-only.* && -d "$TEST_DIR" ]]; then
            rm -rf -- "$TEST_DIR"
        fi
    }
    trap cleanup EXIT

    "$FT5955_CLAIM_ONLY_POLICY" >"$TEST_DIR/polkit.log" 2>&1 &
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
        echo "FAIL: private PolicyKit not ready" >&2
        tail -n 30 "$TEST_DIR/polkit.log" >&2
        exit 4
    fi

    /usr/libexec/fprintd >"$TEST_DIR/fprintd.log" 2>&1 &
    fp_pid=$!
    ready=false
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
        echo "FAIL: private fprintd not ready" >&2
        tail -n 30 "$TEST_DIR/fprintd.log" >&2
        exit 5
    fi

    # Confirm exact rebuilt library loaded BEFORE touching the physical USB reader.
    if ! grep -Fq -- "$FT5955_CLAIM_ONLY_SONAME" "/proc/$fp_pid/maps"; then
        echo "FAIL: daemon did NOT load the new GitHub rebuilt library" >&2
        echo "STOP: Claim not attempted" >&2
        exit 6
    fi
    echo "PASS: private fprintd loaded the exact GitHub rebuilt libfprint."
    echo "=== DEVICE DISCOVERY / CLAIM / RELEASE ONLY ==="
    status=0
    timeout --foreground 65s "$FT5955_CLAIM_ONLY_CLIENT" --claim-only || status=$?
    echo "=== PRIVATE POLICYKIT RESULTS ==="
    grep "PRIVATE BUS TEST PolicyKit:" "$TEST_DIR/polkit.log" || true
    if [[ $status -ne 0 ]]; then
        echo "=== PRIVATE FPRINTD DIAGNOSTICS ==="
        grep -Ei "error|warning|failed|focaltech|ft5955" \
            "$TEST_DIR/fprintd.log" | tail -n 35 || true
    fi
    if [[ $status -eq 0 ]]; then
        echo "PASS: GitHub rebuilt driver: Discover -> Claim -> Release."
    else
        echo "FAIL: Claim-only test status=$status" >&2
    fi
    echo "Disposable private bus/state will be removed."
    exit "$status"
'
