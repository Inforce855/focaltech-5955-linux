#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# LAB-ONLY normal-fprintd enrol/verify bridge to existing non-root MOH/bwrap.
# NEVER enable PAM/fingerprint login. Uses proven staged-lib installer/rollback.
set -Eeuo pipefail
umask 022
[[ $# == 1 && ( "$1" == --activate || "$1" == --rollback ) ]] || {
  echo "Usage: sudo bash $0 --activate | --rollback" >&2; exit 2
}
[[ $EUID -eq 0 && -n "${SUDO_USER:-}" && "$SUDO_USER" != root ]] || {
  echo "STOP: use sudo from normal login, never root login" >&2; exit 2
}
MODE="$1"
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
DISCOVERY="$HERE/manage_ft5955_system_trial.sh"
BROKER="$HERE/ft5955_engine_broker.py"
ROOT=/opt/ft5955-system-trial
LIVE_BROKER="$ROOT/ft5955_engine_broker.py"
MARK="$ROOT/FT5955_LAB_MODE_OWNER"
DROPIN=/etc/systemd/system/fprintd.service.d/90-ft5955-system-trial.conf
SOCKET=/run/ft5955-engine/engine.sock
[[ -f "$DISCOVERY" && ! -L "$DISCOVERY" && -f "$BROKER" && ! -L "$BROKER" ]] || {
  echo "STOP: required helpers absent" >&2; exit 2
}
normal_dropin() {
  cat <<'EOF'
# FT5955 explicit reversible discovery-only trial: no enrolment/verify enabled
[Service]
Environment=LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib
Environment=FT5955_EXPERIMENTAL_ENABLE=0
UnsetEnvironment=FT5955_ENGINE_GATEWAY
EOF
}
live_dropin() {
  cat <<'EOF'
# FT5955 TEST-ONLY: temporary enrol/verify without enabling PAM/login
[Service]
Environment=LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib
Environment=FT5955_EXPERIMENTAL_ENABLE=1
Environment=FT5955_ENGINE_GATEWAY=/opt/ft5955-system-trial/ft5955_engine_broker.py
EOF
}
owned_live() {
  [[ -f "$MARK" && ! -L "$MARK" && "$(cat "$MARK")" == FT5955_LAB_V1 &&
    -f "$LIVE_BROKER" && ! -L "$LIVE_BROKER" && -f "$DROPIN" && ! -L "$DROPIN" ]] &&
  cmp -s <(live_dropin) "$DROPIN"
}
restore_discovery() {
  # Only our precise drop-in is changed. Leave any unexpected file untouched.
  if ! owned_live; then
    echo "STOP: lab override or owner marker changed; inspect manually" >&2
    return 1
  fi
  systemctl stop fprintd.service
  normal_dropin > "$DROPIN.revert"
  chmod 0644 "$DROPIN.revert"
  mv -fT -- "$DROPIN.revert" "$DROPIN"
  systemctl daemon-reload
  rm -- "$LIVE_BROKER" "$MARK"
  echo "PASS: experimental biometric gateway disabled and lab relay removed."
}
if [[ "$MODE" == --rollback ]]; then
  if owned_live; then
    restore_discovery
    bash "$DISCOVERY" --rollback
  elif [[ ! -e "$MARK" && ! -e "$LIVE_BROKER" ]] &&
       [[ -f "$DROPIN" ]] &&
       cmp -s <(normal_dropin) "$DROPIN"; then
    # Recover a completed discovery-only phase.
    bash "$DISCOVERY" --rollback
  elif [[ ! -e "$ROOT" && ! -e "$DROPIN" ]]; then
    echo "PASS: no experimental driver installation remains."
  else
    echo "STOP: unexpected trial files; no blind removal" >&2; exit 2
  fi
  exit 0
fi

# --activate. Require user-running broker, no matching PAM integration.
[[ -S "$SOCKET" && ! -L "$SOCKET" &&
   "$(stat -c %u "$SOCKET")" == "$SUDO_UID" ]] || {
  echo "STOP: root-only client socket not running as invoking user" >&2; exit 2
}
[[ "$(stat -c %a "$SOCKET")" == 600 ]] || {
  echo "STOP: socket mode must be 600" >&2; exit 2
}
[[ ! -e "$MARK" && ! -e "$LIVE_BROKER" ]] || {
  echo "STOP: previous lab relay files exist" >&2; exit 2
}
if rpm -q fprintd-pam >/dev/null 2>&1; then
  echo "STOP: fprintd-pam installed; will not risk real login" >&2; exit 2
fi
# Existing manager independently verifies Nobara RPMs, exact staging SHA,
# no prior local drop-ins, system fprintd inactive and no root-owned overwrites.
stage_live=0
cleanup_on_failure() {
  local rc=$?
  trap - ERR
  if (( stage_live )); then
    echo "Trial setup failed. Restoring discovery-only configuration..." >&2
    if [[ -f "$DROPIN.revert" ]] ; then rm -f -- "$DROPIN.revert"; fi
    if [[ -f "$DROPIN.live" ]] ; then rm -f -- "$DROPIN.live"; fi
    if owned_live; then
      restore_discovery || true
    elif [[ -f "$MARK" && -f "$DROPIN" ]] &&
         cmp -s <(normal_dropin) "$DROPIN"; then
      rm -f -- "$LIVE_BROKER" "$MARK"
    fi
    if [[ -f "$DROPIN" ]] && cmp -s <(normal_dropin) "$DROPIN"; then
      bash "$DISCOVERY" --rollback || echo "WARNING: run --rollback to inspect" >&2
    fi
  fi
  exit "$rc"
}
trap cleanup_on_failure ERR
bash "$DISCOVERY" --activate
stage_live=1
install -m 0644 -o root -g root "$BROKER" "$LIVE_BROKER"
printf '%s\n' FT5955_LAB_V1 > "$MARK"
chmod 0644 "$MARK"
live_dropin > "$DROPIN.live"
chmod 0644 "$DROPIN.live"
mv -fT -- "$DROPIN.live" "$DROPIN"
systemctl daemon-reload
systemctl restart fprintd.service
PID="$(systemctl show fprintd.service --value -p MainPID)"
[[ "$PID" =~ ^[0-9]+$ && "$PID" -gt 1 ]] || {
  echo "STOP: no normal fprintd PID" >&2; false
}
grep -Fq "/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0" "/proc/$PID/maps" || {
  echo "STOP: live normal fprintd loaded wrong libfprint" >&2; false
}
RESULT="$(timeout 15s gdbus call --system \
 --dest net.reactivated.Fprint \
 --object-path /net/reactivated/Fprint/Manager \
 --method net.reactivated.Fprint.Manager.GetDevices)"
[[ "$RESULT" == *"/net/reactivated/Fprint/Device/"* ]] || {
  echo "STOP: lab driver is not discovered" >&2; false
}
trap - ERR
echo "PASS: normal system fprintd PID $PID with experimental driver/gateway installed"
echo "PASS: FT5955 device discovered via real system D-Bus."
echo "LAB ONLY: KDE enrol/verify now possible to TRY, not guaranteed."
echo "NO PAM/login enabled. To restore original: sudo bash $0 --rollback"
