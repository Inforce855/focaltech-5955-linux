#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# FT5955 synthetic DEV-only systemd deployment. NEVER touches fprintd or PAM.
set -Eeuo pipefail
umask 077
MODE="${1:-}"
[[ $# == 1 && "$MODE" == --install || $# == 1 && "$MODE" == --rollback || $# == 1 && "$MODE" == --check ]] || {
 echo "Usage: sudo bash $0 --install|--rollback|--check" >&2; exit 2; }
[[ $EUID == 0 ]] || { echo "Run with sudo" >&2; exit 2; }
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APP=/opt/ft5955-dev
UNITDIR=/etc/systemd/system
SERVICE=ft5955-engine-dev.service
SOCKET=ft5955-engine-dev.socket
ACCOUNT=ft5955-engine
LIVE=/run/ft5955-engine
DEV=/run/ft5955-engine-dev
ORIG=/etc/systemd/system/fprintd.service.d/90-ft5955-system-trial.conf
STATE="$APP/.installed-by-ft5955-dev-script"
assert_live() {
  [[ ! -L "$LIVE" ]] || { echo "STOP: live socket directory is symlink" >&2; exit 1; }
  [[ ! -e "$DEV" && ! -L "$DEV" ]] || { echo "STOP: dev socket directory already exists" >&2; exit 1; }
}
case "$MODE" in
 --check)
  echo "=== DEV status ==="
  getent passwd "$ACCOUNT" || true
  for item in "$APP" "$UNITDIR/$SERVICE" "$UNITDIR/$SOCKET" "$DEV" "$LIVE" "$ORIG"; do
   ls -ld -- "$item" 2>/dev/null || true
  done
  systemctl is-active "$SERVICE" "$SOCKET" || true
  exit 0;;
 --install)
  [[ -d "$ROOT/tools" && -d "$ROOT/systemd" ]] || { echo "STOP: source tree missing" >&2; exit 1; }
  [[ -f "$ROOT/tools/ft5955_dev_mock_server.py" && -f "$ROOT/systemd/$SERVICE" && -f "$ROOT/systemd/$SOCKET" ]] || { echo "STOP: missing source files" >&2; exit 1; }
  for item in "$APP" "$UNITDIR/$SERVICE" "$UNITDIR/$SOCKET"; do
   [[ ! -e "$item" && ! -L "$item" ]] || { echo "STOP: pre-existing dev installation: $item" >&2; exit 1; }
  done
  assert_live
  if getent passwd "$ACCOUNT" >/dev/null; then
   echo "STOP: account $ACCOUNT already exists; refuse to take ownership" >&2; exit 1
  fi
  # Syntax and units validated before mutation.
  python3 - <<PY
import ast
from pathlib import Path
ast.parse(Path("$ROOT/tools/ft5955_dev_mock_server.py").read_text())
PY
  systemd-analyze verify "$ROOT/systemd/$SERVICE" "$ROOT/systemd/$SOCKET" || {
   echo "STOP: systemd unit verification failed" >&2; exit 1; }
  if [[ -e "$LIVE" ]]; then echo "PRESERVING live broker: $LIVE"; fi
  useradd --system --user-group --home-dir /var/lib/ft5955-engine-dev --shell /usr/sbin/nologin "$ACCOUNT"
  install -d -m 0755 -o root -g root "$APP"
  install -m 0644 -o root -g root "$ROOT/tools/ft5955_dev_mock_server.py" "$APP/ft5955_dev_mock_server.py"
  install -m 0644 -o root -g root "$ROOT/systemd/$SERVICE" "$UNITDIR/$SERVICE"
  install -m 0644 -o root -g root "$ROOT/systemd/$SOCKET" "$UNITDIR/$SOCKET"
  touch "$STATE"
  chmod 0600 "$STATE"
  systemctl daemon-reload
  systemctl start "$SOCKET"
  systemctl start "$SERVICE"
  echo "PASS: synthetic DEV service installed and started; no fingerprint authentication available."
  echo "Rollback: sudo bash $0 --rollback"
  ;;
 --rollback)
  [[ -f "$STATE" && ! -L "$STATE" && "$(stat -c %u "$STATE")" == 0 ]] || {
   echo "STOP: installation marker missing or untrusted; no destructive rollback" >&2; exit 1; }
  systemctl stop "$SERVICE" "$SOCKET" || true
  systemctl disable "$SERVICE" "$SOCKET" 2>/dev/null || true
  for file in "$UNITDIR/$SERVICE" "$UNITDIR/$SOCKET" "$APP/ft5955_dev_mock_server.py"; do
    if [[ -f "$file" && ! -L "$file" && "$(stat -c %u "$file")" == 0 ]]; then rm -- "$file"; else
     echo "STOP: ownership changed or file missing: $file" >&2; exit 1; fi
  done
  rm -- "$STATE"
  rmdir -- "$APP"
  systemctl daemon-reload
  if [[ -d "$DEV" && ! -L "$DEV" ]]; then rmdir -- "$DEV" 2>/dev/null || true; fi
  # Account removal is intentionally manual to avoid deleting unrelated data.
  echo "PASS: DEV service files removed. The inactive $ACCOUNT account remains for explicit review."
  echo "Unchanged: live $LIVE, fprintd, PAM, SDDM, enrolled fingerprints."
  ;;
esac
