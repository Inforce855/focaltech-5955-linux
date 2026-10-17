#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Narrow, reversible Nobara fprintd service discovery trial, NOT login setup.
# Never enables experimental biometric operations, PAM, KDE enrolment or MOH.
set -Eeuo pipefail
umask 022

usage() {
  echo "Usage: sudo bash $0 --activate | --rollback | --status" >&2
  exit 2
}
[[ $# == 1 ]] || usage
MODE="$1"
[[ "$MODE" == --activate || "$MODE" == --rollback || "$MODE" == --status ]] || usage
if (( EUID != 0 )) || [[ -z "${SUDO_USER:-}" || "$SUDO_USER" == root ]]; then
  echo "STOP: invoke using sudo from an ordinary user account; never a root shell." >&2
  exit 2
fi

ROOT=/opt/ft5955-system-trial
LIBDIR="$ROOT/lib"
SONAME=libfprint-2.so.2.0.0
BINARY="$LIBDIR/$SONAME"
LINK="$LIBDIR/libfprint-2.so.2"
MARK="$ROOT/FT5955_TRIAL_OWNER"
DROPIN_DIR=/etc/systemd/system/fprintd.service.d
DROPIN="$DROPIN_DIR/90-ft5955-system-trial.conf"
STAGE_USER_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
[[ "$STAGE_USER_HOME" == /home/* && -d "$STAGE_USER_HOME" ]] || {
  echo "STOP: could not validate sudo invoking user's home directory" >&2
  exit 2
}
STAGE="$STAGE_USER_HOME/.local/state/ft5955-system-trial/stage"
SRC="$STAGE/lib/$SONAME"
MANIFEST="$STAGE/SHA256"

dropin_content() {
  cat <<'EOF'
# FT5955 explicit reversible discovery-only trial: no enrolment/verify enabled
[Service]
Environment=LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib
Environment=FT5955_EXPERIMENTAL_ENABLE=0
UnsetEnvironment=FT5955_ENGINE_GATEWAY
EOF
}
# Only undo files this script intentionally created, and only if marker and
# exact contents show that the installation is still ours.
owned_state() {
  [[ -f "$MARK" && ! -L "$MARK" && -f "$DROPIN" && ! -L "$DROPIN" &&
     -f "$BINARY" && ! -L "$BINARY" && -L "$LINK" &&
     "$(readlink -- "$LINK")" == "$SONAME" ]] || return 1
  cmp -s <(dropin_content) "$DROPIN" || return 1
  [[ "$(cat -- "$MARK")" =~ ^[0-9a-f]{64}$ ]] || return 1
  [[ "$(sha256sum "$BINARY" | cut -d' ' -f1)" == "$(cat -- "$MARK")" ]]
}
rollback_owned() {
  if ! owned_state; then
    echo "STOP: trial files no longer exactly match; manual review required." >&2
    return 1
  fi
  echo "Stopping ONLY fprintd.service, then restoring packaged runtime..."
  systemctl stop fprintd.service
  rm -- "$DROPIN"
  systemctl daemon-reload
  if systemctl show fprintd.service --value -p DropInPaths | grep -Fq "$DROPIN"; then
    echo "STOP: trial override still visible in systemd configuration!" >&2
    return 1
  fi
  rm -- "$LINK" "$BINARY" "$MARK"
  rmdir -- "$LIBDIR" "$ROOT"
  rmdir -- "$DROPIN_DIR" 2>/dev/null || true
  echo "PASS: trial service override and separate binary removed."
  echo "PASS: original RPM-owned libfprint and fprintd untouched; packaged service restored."
  echo "Normal D-Bus activation will next load original system libfprint."
}

case "$MODE" in
--status)
  echo "=== TRIAL STATUS (READ ONLY) ==="
  echo "System fprintd: $(systemctl show fprintd.service --value -p ActiveState)"
  echo "Local trial marker: $([[ -e "$MARK" ]] && echo present || echo absent)"
  echo "Service drop-in: $([[ -e "$DROPIN" ]] && echo present || echo absent)"
  if owned_state; then echo "TRIAL FILES: verified"; fi
  echo "Runtime drop-ins: $(systemctl show fprintd.service --value -p DropInPaths)"
  exit 0
  ;;
--rollback)
  if [[ ! -e "$ROOT" && ! -e "$DROPIN" ]]; then
    echo "PASS: no FT5955 trial installation exists; nothing to roll back."
    exit 0
  fi
  rollback_owned
  exit 0
  ;;
esac

# --activate: checked, one-time installation. No replacement of RPM files.
for exe in systemctl rpm install sha256sum gdbus timeout cmp getent stat; do
  command -v "$exe" >/dev/null || { echo "STOP: missing $exe" >&2; exit 2; }
done
[[ ! -e "$ROOT" && ! -L "$ROOT" && ! -e "$DROPIN" && ! -L "$DROPIN" ]] || {
  echo "STOP: trial install already exists (or collision). Do not overwrite." >&2
  exit 2
}
[[ "$(systemctl show fprintd.service --value -p LoadState)" == loaded &&
   "$(systemctl show fprintd.service --value -p ActiveState)" == inactive &&
   "$(systemctl show fprintd.service --value -p MainPID)" == 0 &&
   "$(systemctl show fprintd.service --value -p FragmentPath)" == /usr/lib/systemd/system/fprintd.service &&
   "$(systemctl show fprintd.service --value -p User)" == "" ]] || {
  echo "STOP: fprintd system service changed or is running; nothing installed." >&2
  exit 2
}
[[ "$(systemctl show fprintd.service --value -p DropInPaths)" == /usr/lib/systemd/system/service.d/10-timeout-abort.conf ]] || {
  echo "STOP: fprintd drop-ins changed since reviewed preflight." >&2
  exit 2
}
[[ "$(systemctl show fprintd.service --value -p ProtectHome)" == yes &&
   "$(systemctl show fprintd.service --value -p ProtectSystem)" == strict ]] || {
  echo "STOP: unexpected fprintd security settings." >&2; exit 2
}
[[ "$(rpm -q --qf '%{VERSION}-%{RELEASE}' libfprint)" == 1.94.100-1.fc44 &&
   "$(rpm -q --qf '%{VERSION}-%{RELEASE}' fprintd)" == 1.94.5-5.fc44 ]] || {
  echo "STOP: fprintd/libfprint RPM versions changed since the preflight." >&2
  exit 2
}
if rpm -q fprintd-pam >/dev/null 2>&1; then
  echo "STOP: fprintd-pam now present; review active authentication first." >&2
  exit 2
fi
[[ -f "$SRC" && ! -L "$SRC" && -f "$MANIFEST" && ! -L "$MANIFEST" ]] || {
  echo "STOP: no verified staged FocalTech shared library. Run --stage as user." >&2
  exit 2
}
[[ "$(stat -c '%u' -- "$SRC")" == "$SUDO_UID" &&
   "$(stat -c '%u' -- "$MANIFEST")" == "$SUDO_UID" &&
   "$(stat -c '%a' -- "$SRC")" == 600 ]] || {
  echo "STOP: staged library ownership/mode unexpected." >&2; exit 2
}
read -r expected relative < "$MANIFEST"
[[ "$expected" =~ ^[0-9a-f]{64}$ && "$relative" == "lib/$SONAME" ]] || {
  echo "STOP: stage manifest malformed." >&2; exit 2
}
actual="$(sha256sum "$SRC" | cut -d' ' -f1)"
[[ "$expected" == "$actual" ]] || {
  echo "STOP: staged library SHA-256 mismatch." >&2; exit 2
}
echo "PASS: packaged service unchanged; staged library verified ($actual)"
echo "Installing isolated, root-owned trial files; NO RPM replacement or PAM edits."

IN_PROGRESS=0
rollback_error() {
  local failure="$?"
  trap - ERR
  if [[ $IN_PROGRESS == 1 ]]; then
    echo "Trial activation failed. Attempting automatic rollback." >&2
    if owned_state; then
      rollback_owned || echo "WARNING: automatic rollback failed; run --rollback/review immediately." >&2
    else
      # Only remove the known files we created if no other file has appeared.
      systemctl stop fprintd.service >/dev/null 2>&1 || true
      if [[ -e "$DROPIN" ]] && cmp -s <(dropin_content) "$DROPIN"; then
        rm -- "$DROPIN"
      fi
      systemctl daemon-reload || true
      if [[ -f "$MARK" && -f "$BINARY" &&
            "$(sha256sum "$BINARY" | cut -d' ' -f1)" == "$(cat "$MARK")" ]]; then
        rm -f -- "$LINK" "$BINARY" "$MARK"
        rmdir -- "$LIBDIR" "$ROOT" 2>/dev/null || true
      fi
      rmdir -- "$DROPIN_DIR" 2>/dev/null || true
    fi
  fi
  exit "$failure"
}
trap rollback_error ERR
install -d -m 0755 -o root -g root "$LIBDIR"
IN_PROGRESS=1
install -m 0644 -o root -g root "$SRC" "$BINARY"
ln -s "$SONAME" "$LINK"
printf '%s\n' "$actual" > "$MARK"
chmod 0644 "$MARK"
install -d -m 0755 -o root -g root "$DROPIN_DIR"
dropin_content > "$DROPIN"
chmod 0644 "$DROPIN"
systemctl daemon-reload
systemctl start fprintd.service
PID="$(systemctl show fprintd.service --value -p MainPID)"
[[ "$PID" =~ ^[0-9]+$ && "$PID" -gt 1 ]] || {
  echo "STOP: started service has no usable MainPID." >&2; false
}
grep -Fq -- "$BINARY" "/proc/$PID/maps" || {
  echo "STOP: system fprintd did not map the staged trial libfprint." >&2; false
}
echo "PASS: system fprintd PID $PID mapped exact root-owned experimental .so"
RESULT="$(timeout 15s gdbus call --system \
  --dest net.reactivated.Fprint \
  --object-path /net/reactivated/Fprint/Manager \
  --method net.reactivated.Fprint.Manager.GetDevices)"
printf 'SYSTEM GETDEVICES: %s\n' "$RESULT"
[[ "$RESULT" == *"/net/reactivated/Fprint/Device/"* ]] || {
  echo "STOP: system service did not report a fingerprint device." >&2; false
}
IN_PROGRESS=0
trap - ERR
echo "PASS: system-service FT5955 discovery trial active (no biometric operations)."
echo "ROLLBACK: sudo bash <THIS_SCRIPT> --rollback"
echo "Password login and Nobara RPM-owned libfprint remain unchanged."
