#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Read-only binary and UID isolation preflight. No MOH execution.
set -Eeuo pipefail
[[ $# == 1 ]] || { echo "Usage: bash $0 /path/to/live-identify" >&2; exit 2; }
BIN="$1"
[[ -f "$BIN" && ! -L "$BIN" ]] || { echo "STOP: missing binary or symlink" >&2; exit 2; }
echo "=== COMPILED MOH BINARY ==="
file "$BIN"
sha256sum "$BIN"
stat -c 'owner=%U group=%G mode=%a size=%s' "$BIN"
echo
echo "=== SERVICE ACCOUNT AND BINARY PATH ACCESS ==="
getent passwd ft5955-engine
namei -l "$BIN"
echo
echo "=== COMPILER LINKAGE (STATIC INSPECTION ONLY) ==="
readelf -h "$BIN" | grep -E 'Class:|Machine:|Type:'
readelf -d "$BIN" | grep 'NEEDED' || true
echo
echo "=== DEV SERVICE ==="
systemctl show ft5955-engine-dev.service -p ActiveState -p User -p Group -p ExecStart --no-pager
echo
echo "PASS: static binary inspection completed; NO engine execution or DLL loading."
echo "NOTICE: binary in user-owned temporary directory is NOT trusted for PAM or service promotion."
