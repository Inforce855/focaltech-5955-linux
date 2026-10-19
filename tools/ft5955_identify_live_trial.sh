#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Verified, reversible FT5955 IDENTIFY .so swap for ALREADY ENABLED fingerprint PAM.
# Only the installed experimental libfprint binary and its SHA256 marker can change.
# No edits to PAM, fprintd drop-ins, user templates, systemd sockets or MOH service.
set -Eeuo pipefail
umask 077

[[ $# -eq 1 && ( "$1" == --status || "$1" == --activate || "$1" == --rollback ) ]] || {
  echo "Usage: sudo bash $0 --status|--activate|--rollback" >&2
  exit 2
}
MODE="$1"
[[ $EUID -eq 0 && -n "${SUDO_USER:-}" && "$SUDO_USER" != root &&
   "${SUDO_UID:-}" =~ ^[0-9]+$ ]] || {
  echo "STOP: invoke via sudo from the ordinary user session" >&2; exit 2;
}
ROOT=/opt/ft5955-system-trial
LIBDIR="$ROOT/lib"
SONAME=libfprint-2.so.2.0.0
LIVE="$LIBDIR/$SONAME"
LINK="$LIBDIR/libfprint-2.so.2"
MARK="$ROOT/FT5955_TRIAL_OWNER"
BACK_DIR="$ROOT/.identify-rollback-20261019"
BACK_LIB="$BACK_DIR/$SONAME"
BACK_MARK="$BACK_DIR/FT5955_TRIAL_OWNER"
OLD=02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28
NEW=70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd
OVERRIDE90=/etc/systemd/system/fprintd.service.d/90-ft5955-system-trial.conf
OVERRIDE95=/etc/systemd/system/fprintd.service.d/95-ft5955-moh-dev-gateway.conf
HOME_DIR="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
[[ "$HOME_DIR" == /home/* && -d "$HOME_DIR" && ! -L "$HOME_DIR" ]] || {
  echo "STOP: unexpected invoking user home directory" >&2; exit 2;
}
STAGE="$HOME_DIR/.local/state/ft5955-system-trial/stage-identify"
STAGED="$STAGE/lib/$SONAME"
MANIFEST="$STAGE/SHA256"

fail() { echo "STOP: $*" >&2; exit 1; }
sha() { sha256sum -- "$1" | cut -d' ' -f1; }
regular_root() {
  [[ -f "$1" && ! -L "$1" &&
     "$(stat -c %u -- "$1")" == 0 &&
     "$(stat -c %g -- "$1")" == 0 ]] ||
    fail "not an expected root-owned regular file: $1"
}
layout() {
  [[ -d "$ROOT" && ! -L "$ROOT" && -d "$LIBDIR" && ! -L "$LIBDIR" ]] ||
    fail "installed FT5955 directory layout changed"
  [[ "$(stat -c %u "$ROOT")" == 0 && "$(stat -c %u "$LIBDIR")" == 0 ]] ||
    fail "installed FT5955 directory ownership changed"
  regular_root "$LIVE"
  regular_root "$MARK"
  [[ -L "$LINK" && "$(readlink -- "$LINK")" == "$SONAME" ]] ||
    fail "installed libfprint SONAME link changed"
}
known_service() {
  regular_root "$OVERRIDE90"
  regular_root "$OVERRIDE95"
  grep -Fxq 'Environment=LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib' "$OVERRIDE90" ||
    fail "libfprint load path changed"
  grep -Fxq 'Environment=FT5955_EXPERIMENTAL_ENABLE=1' "$OVERRIDE90" ||
    fail "fingerprint driver enablement changed"
  grep -Fxq 'Environment=FT5955_ENGINE_GATEWAY=/opt/ft5955-dev/ft5955_dev_relay.py' "$OVERRIDE95" ||
    fail "protected MOH gateway changed"
  local effective
  effective="$(systemctl show --value -p Environment fprintd.service)"
  [[ "$effective" == *"LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib"* &&
     "$effective" == *"FT5955_EXPERIMENTAL_ENABLE=1"* &&
     "$effective" == *"FT5955_ENGINE_GATEWAY=/opt/ft5955-dev/ft5955_dev_relay.py"* ]] ||
    fail "unexpected effective fprintd environment"
}
idle() {
  [[ "$(systemctl show --value -p ActiveState fprintd.service)" == inactive &&
     "$(systemctl show --value -p MainPID fprintd.service)" == 0 ]] ||
    fail "fprintd is running; stop it separately after completing authentication"
}
backup_ok() {
  [[ -d "$BACK_DIR" && ! -L "$BACK_DIR" &&
     "$(stat -c %u "$BACK_DIR")" == 0 &&
     "$(stat -c %a "$BACK_DIR")" == 700 ]] ||
    fail "root-only rollback directory missing or changed"
  regular_root "$BACK_LIB"
  regular_root "$BACK_MARK"
  [[ "$(sha "$BACK_LIB")" == "$OLD" && "$(cat "$BACK_MARK")" == "$OLD" ]] ||
    fail "original driver backup/marker failed integrity check"
}
stage_ok() {
  [[ -d "$STAGE" && ! -L "$STAGE" && -d "$STAGE/lib" &&
     ! -L "$STAGE/lib" && -f "$STAGED" && ! -L "$STAGED" &&
     -f "$MANIFEST" && ! -L "$MANIFEST" ]] ||
    fail "staged identify driver/manifest not regular files"
  [[ "$(stat -c %u "$STAGED")" == "$SUDO_UID" &&
     "$(stat -c %a "$STAGED")" == 600 &&
     "$(stat -c %u "$MANIFEST")" == "$SUDO_UID" ]] ||
    fail "staged candidate ownership or permissions changed"
  local expected rel extra
  read -r expected rel extra < "$MANIFEST" ||
    fail "cannot parse identify stage manifest"
  [[ "$expected" == "$NEW" && "$rel" == "lib/$SONAME" &&
     -z "${extra:-}" && "$(sha "$STAGED")" == "$NEW" ]] ||
    fail "staged identify candidate SHA256 mismatch"
}
temporary=""
tmpmarker=""
cleanup_temp() {
  [[ -z "$temporary" ]] || rm -f -- "$temporary"
  [[ -z "$tmpmarker" ]] || rm -f -- "$tmpmarker"
}
atomic_library() {
  temporary="$(mktemp "$LIBDIR/.identify-lib.XXXXXXXX")"
  install -m 0644 -o root -g root -- "$1" "$temporary"
  [[ "$(sha "$temporary")" == "$2" ]] ||
    fail "staged temporary library checksum mismatch"
  mv -fT -- "$temporary" "$LIVE"
  temporary=""
}
atomic_marker() {
  tmpmarker="$(mktemp "$ROOT/.identify-marker.XXXXXXXX")"
  printf '%s\n' "$1" > "$tmpmarker"
  chmod 0644 -- "$tmpmarker"
  mv -fT -- "$tmpmarker" "$MARK"
  tmpmarker=""
}
layout
case "$MODE" in
  --status)
    echo "LIVE_SHA=$(sha "$LIVE")"
    echo "MARKER_SHA=$(cat "$MARK")"
    if [[ -e "$BACK_DIR" || -L "$BACK_DIR" ]]; then
      backup_ok
      echo "ROLLBACK_BACKUP=verified"
    else
      echo "ROLLBACK_BACKUP=not-yet-created"
    fi
    echo "FPRINTD_STATE=$(systemctl show --value -p ActiveState fprintd.service)"
    echo "READ ONLY: no changes"
    exit 0
    ;;
  --activate)
    known_service
    stage_ok
    [[ "$(sha "$LIVE")" == "$OLD" && "$(cat "$MARK")" == "$OLD" ]] ||
      fail "original live driver or marker differs from documented good version"
    idle
    if [[ -e "$BACK_DIR" || -L "$BACK_DIR" ]]; then
      backup_ok
    else
      mkdir -m 0700 -- "$BACK_DIR"
      install -m 0600 -o root -g root -- "$LIVE" "$BACK_LIB"
      install -m 0600 -o root -g root -- "$MARK" "$BACK_MARK"
      backup_ok
    fi
    ;;
  --rollback)
    backup_ok
    [[ "$(sha "$LIVE")" == "$OLD" || "$(sha "$LIVE")" == "$NEW" ]] ||
      fail "unrecognised live binary; refusing to replace"
    [[ "$(cat "$MARK")" == "$OLD" || "$(cat "$MARK")" == "$NEW" ]] ||
      fail "unrecognised installation marker; refusing to replace"
    idle
    ;;
esac

trap cleanup_temp EXIT
if [[ "$MODE" == --activate ]]; then
  echo "PASS: original root-owned library and marker securely backed up."
  atomic_library "$STAGED" "$NEW"
  atomic_marker "$NEW"
  [[ "$(sha "$LIVE")" == "$NEW" && "$(cat "$MARK")" == "$NEW" ]] ||
    fail "post-install mismatch: use --rollback immediately"
  echo "PASS: identify library selected for the next on-demand fprintd start."
  echo "PAM, both service overrides, protected MOH and enrolled prints unchanged."
  echo "ROLLBACK: sudo -n bash $0 --rollback"
else
  atomic_library "$BACK_LIB" "$OLD"
  atomic_marker "$OLD"
  [[ "$(sha "$LIVE")" == "$OLD" && "$(cat "$MARK")" == "$OLD" ]] ||
    fail "rollback verification failed"
  echo "PASS: original known-good libfprint and original marker restored."
fi
