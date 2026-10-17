#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# A SHORT-LIVED lab-only test, not an installed login method.
# Starts the previously working user's MOH+bwrap under THEIR UID, joins
# normal fprintd via the root-owned relay and protected Unix socket.
# NEVER touch PAM/SDDM, never run the proprietary DLL as root.
set -Eeuo pipefail
umask 077
[[ $EUID -ne 0 && $# == 1 ]] || {
  echo "Usage (normal user, NEVER sudo): bash $0 --start | --stop" >&2; exit 2
}
case "$1" in
  --start|--stop) MODE="$1";;
  *) echo "Usage: bash $0 --start | --stop" >&2; exit 2;;
esac
REPO="$(cd -- "$(dirname -- "$0")/.." && pwd)"
BROKER="$REPO/tools/ft5955_engine_broker.py"
GATEWAY="$REPO/driver/live-snapshot-2026-10-16/engine/engine_gateway.py"
MOH="$HOME/Projects/focaltech-5955-moh-test"
INSTALLER="$REPO/tools/manage_ft5955_kde_trial.sh"
SOCKET_DIR=/run/ft5955-engine
SOCKET="$SOCKET_DIR/engine.sock"
STATE="$HOME/.local/state/ft5955-system-trial"
PIDFILE="$STATE/kde-trial-broker.pid"
LOGFILE="$STATE/kde-trial-broker.log"

stop_broker() {
  if [[ -f "$PIDFILE" && ! -L "$PIDFILE" ]]; then
    pid="$(cat "$PIDFILE")"
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      args="$(ps -p "$pid" -o args= || true)"
      if [[ "$args" == *ft5955_engine_broker.py* &&
            "$args" == *--serve-user-trial* ]]; then
        kill "$pid"
        for i in {1..30}; do
          kill -0 "$pid" 2>/dev/null || break
          sleep 0.1
        done
        if kill -0 "$pid" 2>/dev/null; then
          echo "WARNING: user broker PID $pid still alive; inspect it." >&2
          return 1
        fi
      else
        echo "STOP: PID reused or process changed: no blind kill." >&2
        return 1
      fi
    fi
    rm -f -- "$PIDFILE"
  fi
  if [[ -S "$SOCKET" && ! -L "$SOCKET" &&
        "$(stat -c %u "$SOCKET")" == "$(id -u)" ]]; then
    rm -- "$SOCKET"
  fi
  if [[ -d "$SOCKET_DIR" ]]; then
    sudo rmdir -- "$SOCKET_DIR" 2>/dev/null || true
  fi
}

if [[ "$MODE" == --stop ]]; then
  # Roll back the production service BEFORE stopping the user matcher, in
  # case the KDE GUI is still trying to use an active fingerprint operation.
  sudo bash "$INSTALLER" --rollback
  stop_broker
  echo "PASS: experimental driver removed; original Nobara fprintd restored."
  echo "No PAM changes were made; existing saved test fingerprints (if any)"
  echo "are NOT automatically deleted from fprintd storage."
  exit 0
fi

# --start
[[ ! -e "$PIDFILE" && ! -e "$SOCKET" && ! -L "$SOCKET" &&
   ! -e "$SOCKET_DIR" && ! -L "$SOCKET_DIR" ]] || {
  echo "STOP: existing broker or live trial state; run --stop/review first." >&2; exit 2
}
[[ -f "$BROKER" && -f "$GATEWAY" &&
   -f "$MOH/tools/test_moh_isolated_live_identify.sh" ]] || {
  echo "STOP: audited MOH gateway source is missing." >&2; exit 2
}
if rpm -q fprintd-pam >/dev/null 2>&1; then
  echo "STOP: fingerprint PAM package present; trial is not safe for login." >&2; exit 2
fi
mkdir -p -m 0700 -- "$STATE"
# /run/user/$UID is unavailable to system fprintd due to ProtectHome=yes.
# Only prepare a root-traversable private socket location in /run.
sudo install -d -m 0700 -o "$(id -un)" -g "$(id -gn)" -- "$SOCKET_DIR"
( nohup python3 "$BROKER" --serve --serve-user-trial \
    --gateway "$GATEWAY" --moh-dir "$MOH" \
    > "$LOGFILE" 2>&1 < /dev/null & echo $! > "$PIDFILE" )
ready=0
for i in {1..80}; do
  if [[ -S "$SOCKET" ]]; then ready=1; break; fi
  pid="$(cat "$PIDFILE")"
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 0.1
done
if [[ $ready -ne 1 ]]; then
  echo "STOP: MOH broker did not create private Unix socket." >&2
  sed -n '1,30p' "$LOGFILE" >&2 || true
  stop_broker
  exit 1
fi
if ! sudo bash "$INSTALLER" --activate; then
  echo "STOP: fprintd laboratory activation failed; attempting rollback." >&2
  sudo bash "$INSTALLER" --rollback || true
  stop_broker || true
  exit 1
fi
echo "PASS: FT5955 system driver and USER-session MOH broker active."
echo "Only now try KDE > System Settings > Users > Fingerprint authentication."
echo "This is experimental ENROL/VERIFY, NOT fingerprint login. No PAM changes."
echo "ROLLBACK: bash '$REPO/tools/ft5955_kde_trial.sh' --stop"
