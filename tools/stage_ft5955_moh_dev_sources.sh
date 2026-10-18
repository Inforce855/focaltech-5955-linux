#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Non-executing MOH development SOURCE staging. Never changes live matcher/PAM.
set -Eeuo pipefail
umask 077
[[ $# == 1 && "$1" == --stage ]] || { echo "Usage: sudo bash $0 --stage" >&2; exit 2; }
[[ $EUID == 0 ]] || { echo "STOP: run with sudo" >&2; exit 2; }
ACCOUNT=ft5955-engine
SOURCE_USER="${SUDO_USER:-}"
[[ -n "$SOURCE_USER" && "$SOURCE_USER" != root ]] || { echo "STOP: sudo from a regular user required" >&2; exit 2; }
getent passwd "$ACCOUNT" >/dev/null || { echo "STOP: missing service account" >&2; exit 2; }
SOURCE_HOME="$(getent passwd "$SOURCE_USER" | cut -d: -f6)"
SOURCE="$SOURCE_HOME/Projects/focaltech-5955-moh-test"
DEST=/opt/ft5955-dev/real-moh-source
DLL=/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll
[[ -d /opt/ft5955-dev && ! -L /opt/ft5955-dev ]] || { echo "STOP: independent dev installation missing" >&2; exit 2; }
[[ ! -e "$DEST" && ! -L "$DEST" ]] || { echo "STOP: staging already exists; refusing overwrite" >&2; exit 2; }
[[ -d "$SOURCE" && ! -L "$SOURCE" && -f "$DLL" && ! -L "$DLL" ]] || { echo "STOP: MOH source or DLL missing" >&2; exit 2; }
[[ "$(stat -c %u "$DLL")" == 0 && "$(stat -c %a "$DLL")" =~ ^(644|640|600|444|440|400)$ ]] || { echo "STOP: DLL ownership or permissions" >&2; exit 2; }
FILES=(
 tools/test_moh_isolated_live_identify.sh
 tools/moh_engine_preflight.py
 engine/ft_engine.c
)
for rel in "${FILES[@]}"; do
 [[ -f "$SOURCE/$rel" && ! -L "$SOURCE/$rel" ]] || { echo "STOP: missing or linked MOH source $rel" >&2; exit 2; }
done
# A staging copy is NOT a security validation of account-controlled inputs.
install -d -m 0755 -o root -g root "$DEST" "$DEST/tools" "$DEST/engine"
for rel in "${FILES[@]}"; do
 install -m 0644 -o root -g root "$SOURCE/$rel" "$DEST/$rel"
done
(
 cd "$DEST"
 sha256sum "${FILES[@]}" > SHA256SUMS
 chown root:root SHA256SUMS
 chmod 0644 SHA256SUMS
)
echo "PASS: source-only MOH staging into $DEST"
echo "NOT INSTALLED AS MATCHER. No DLL execution, PAM, fprintd, socket or systemd change."
echo "CAUTION: staged source came from user's original tree; audit is required before trusting it."
