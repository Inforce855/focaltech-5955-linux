#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Stages complete, independently verified MOH build inputs. Never executes them.
set -Eeuo pipefail
umask 077
[[ ${1:-} == --stage && $# == 1 ]] || { echo "Usage: sudo bash $0 --stage" >&2; exit 2; }
[[ $EUID == 0 && -n ${SUDO_USER:-} && ${SUDO_USER} != root ]] || { echo "STOP: sudo from user required" >&2; exit 2; }
HOME_SOURCE="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
SRC="$HOME_SOURCE/Projects/focaltech-5955-moh-test"
DEST=/opt/ft5955-dev/real-moh-source
[[ -d "$SRC/engine" && -d "$SRC/tools" && -d "$DEST/engine" && -d "$DEST/tools" ]] || { echo "STOP: source or existing dev stage missing" >&2; exit 2; }
for d in /opt/ft5955-dev "$DEST" "$DEST/engine" "$DEST/tools"; do
 [[ ! -L "$d" && "$(stat -c %u "$d")" == 0 && ! -w "$d" || ! -L "$d" && "$(stat -c %u "$d")" == 0 ]] || { echo "STOP: untrusted stage directory $d" >&2; exit 2; }
 [[ $(( 8#$(stat -c %a "$d") & 8#022 )) == 0 ]] || { echo "STOP: writable stage directory $d" >&2; exit 2; }
done
mapfile -d '' SOURCES < <(find "$SRC/engine" -maxdepth 1 -type f \( -name '*.c' -o -name '*.h' \) -print0)
[[ ${#SOURCES[@]} == 44 ]] || { echo "STOP: unexpected engine source count: ${#SOURCES[@]}" >&2; exit 2; }
SOURCES+=("$SRC/tools/moh_engine_live_identify.c" "$SRC/tools/moh_engine_preflight.py" "$SRC/tools/test_moh_isolated_live_identify.sh")
for source in "${SOURCES[@]}"; do
 [[ -f "$source" && ! -L "$source" ]] || { echo "STOP: missing/source symlink $source" >&2; exit 2; }
 rel="${source#"$SRC"/}"
 target="$DEST/$rel"
 if [[ -e "$target" || -L "$target" ]]; then
   [[ -f "$target" && ! -L "$target" && "$(stat -c %u "$target")" == 0 ]] || { echo "STOP: unsafe staged file $rel" >&2; exit 2; }
   cmp -s -- "$source" "$target" || { echo "STOP: staged content mismatch $rel" >&2; exit 2; }
 fi
done
for source in "${SOURCES[@]}"; do
 rel="${source#"$SRC"/}"
 target="$DEST/$rel"
 if [[ ! -e "$target" ]]; then
   install -m 0644 -o root -g root -- "$source" "$target"
 fi
done
echo "=== STAGED SOURCE CHECK ==="
for source in "${SOURCES[@]}"; do
 rel="${source#"$SRC"/}"
 cmp -s "$source" "$DEST/$rel" || exit 1
done
echo "PASS: 47 build/launcher candidates present and byte-identical in protected dev tree."
echo "No DLL execution; no service, socket, PAM, fprintd or live matcher changes."
