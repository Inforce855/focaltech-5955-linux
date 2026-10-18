#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Guarded dev-only deployment of real enrol/verify MOH protocol.
# No changes to fprintd, KDE, PAM, authselect, sudo, SDDM or live broker.
set -Eeuo pipefail
umask 077
[[ $# -eq 1 && ( "$1" == --activate || "$1" == --rollback || "$1" == --status ) ]] || {
  echo "Usage: sudo bash $0 --activate|--rollback|--status" >&2; exit 2;
}
[[ $EUID -eq 0 ]] || { echo "STOP: requires sudo" >&2; exit 2; }
MODE="$1"
SOURCE="$(cd -- "$(dirname -- "$0")/.." && pwd)"
APP=/opt/ft5955-dev
STAGED="$APP/real-moh-source"
UNIT=/etc/systemd/system/ft5955-engine-dev.service
BACKUP=/etc/systemd/system/ft5955-engine-dev.service.before-protocol
MARKER="$APP/.template-protocol-enabled"
ACCOUNT=ft5955-engine
SOCKET=/run/ft5955-engine-dev/engine.sock
SERVICE=ft5955-engine-dev.service

[[ -d "$APP" && ! -L "$APP" && -f "$UNIT" && ! -L "$UNIT" ]] || {
  echo "STOP: known installed independent dev service missing" >&2; exit 2;
}
[[ "$(stat -c %u "$APP")" == 0 && "$(stat -c %u "$UNIT")" == 0 ]] || {
  echo "STOP: ownership of dev service is unexpected" >&2; exit 2;
}
getent passwd "$ACCOUNT" >/dev/null || { echo "STOP: dedicated account absent" >&2; exit 2; }

if [[ "$MODE" == --status ]]; then
  systemctl show "$SERVICE" -p ActiveState -p ExecStart -p RestrictAddressFamilies --no-pager
  if [[ -f "$MARKER" ]]; then echo "MOH protocol trial active"; else echo "Not marked active"; fi
  exit 0
fi
if [[ "$MODE" == --rollback ]]; then
  [[ -f "$MARKER" && ! -L "$MARKER" && -f "$BACKUP" && ! -L "$BACKUP" ]] || {
    echo "STOP: known protocol installation marker/backup missing" >&2; exit 2;
  }
  grep -Fq 'ft5955_dev_protocol_server.py' "$UNIT" || {
    echo "STOP: current dev unit has changed; manual review before rollback" >&2; exit 2;
  }
  cp -a -- "$BACKUP" "$UNIT"
  systemctl daemon-reload
  systemctl restart "$SERVICE"
  rm -f -- "$MARKER"
  echo "PASS: original development service restored; staged files kept for review."
  echo "PRESERVED: fprintd, original live MOH broker, PAM and enrolled fingerprints."
  exit 0
fi

# ACTIVATION: do not replace an unknown or previously modified service.
[[ ! -e "$MARKER" && ! -L "$MARKER" && ! -e "$BACKUP" && ! -L "$BACKUP" ]] || {
  echo "STOP: previous protocol trial or backup exists; inspect instead of overwriting" >&2; exit 2;
}
grep -Fq 'ft5955_dev_real_startup_server.py' "$UNIT" || {
  echo "STOP: expected real-startup dev unit is not installed" >&2; exit 2;
}
grep -Fxq 'RestrictAddressFamilies=AF_UNIX AF_NETLINK' "$UNIT" || {
  echo "STOP: validated dev namespace configuration missing" >&2; exit 2;
}
[[ -d "$STAGED/tools" && -f "$STAGED/tools/test_moh_isolated_live_identify.sh" ]] || {
  echo "STOP: audited protected source tree is absent" >&2; exit 2;
}
[[ -f /usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll ]] || {
  echo "STOP: pinned vendor DLL missing" >&2; exit 2;
}
[[ -f "$SOURCE/driver/live-snapshot-2026-10-16/engine/template_session.c" ]] || {
  echo "STOP: immutable working template protocol missing" >&2; exit 2;
}
[[ -f "$SOURCE/systemd/ft5955-engine-dev-protocol.service" ]] || {
  echo "STOP: new protocol dev unit missing" >&2; exit 2;
}
systemd-analyze verify "$SOURCE/systemd/ft5955-engine-dev-protocol.service" || {
  echo "STOP: systemd unit syntax invalid" >&2; exit 2;
}

# Staging is exact-match-only; never clobber a pre-existing protected file.
stage() {
  local from="$1" to="$2"
  [[ -f "$from" && ! -L "$from" ]] || { echo "STOP: missing/symlink source" >&2; exit 2; }
  if [[ -e "$to" || -L "$to" ]]; then
    [[ -f "$to" && ! -L "$to" && "$(stat -c %u "$to")" == 0 ]] || {
      echo "STOP: unexpected staged file" >&2; exit 2;
    }
    cmp -s -- "$from" "$to" || { echo "STOP: staged source differs; review first" >&2; exit 2; }
  else
    install -o root -g root -m 0644 "$from" "$to"
  fi
}
stage "$SOURCE/driver/live-snapshot-2026-10-16/engine/template_session.c" "$STAGED/tools/ft5955_template_session.c"
for name in build_ft5955_moh_template_dev.py ft5955_dev_template_launcher.py ft5955_dev_template_gateway.py ft5955_dev_protocol_server.py ft5955_dev_relay.py ft5955_engine_broker.py; do
  stage "$SOURCE/tools/$name" "$APP/$name"
done

# Syntax checks are performed before compilation or service replacement.
python3 -I -B - "$APP" <<'PY'
import ast,sys
from pathlib import Path
root=Path(sys.argv[1])
for p in root.glob("*.py"):
    if p.name in {
      "build_ft5955_moh_template_dev.py",
      "ft5955_dev_template_launcher.py",
      "ft5955_dev_template_gateway.py",
      "ft5955_dev_protocol_server.py",
      "ft5955_dev_relay.py",
      "ft5955_engine_broker.py",
    }:
        ast.parse(p.read_text())
print("PASS: protected Python source parses")
PY

# Build exclusively from staged root-owned C sources, as non-root UID955.
BUILD="$(mktemp -d /var/tmp/ft5955-template.XXXXXXXX)"
chown "$ACCOUNT:$ACCOUNT" "$BUILD"
chmod 0700 "$BUILD"
cleanup() { rm -rf -- "$BUILD"; }
trap cleanup EXIT
runuser -u "$ACCOUNT" -- /usr/bin/python3 -I -B   "$APP/build_ft5955_moh_template_dev.py" --output-dir "$BUILD"
[[ -s "$BUILD/live-template" && ! -L "$BUILD/live-template" ]] || {
  echo "STOP: compiled protected MOH protocol binary missing" >&2; exit 2;
}
if [[ -e "$APP/live-template" || -L "$APP/live-template" ]]; then
  echo "STOP: existing live-template; inspect before overwriting" >&2; exit 2
fi
install -o root -g "$ACCOUNT" -m 0550 "$BUILD/live-template" "$APP/live-template"
cmp -s "$BUILD/live-template" "$APP/live-template" || {
  echo "STOP: binary staging mismatch" >&2; exit 2;
}

# Preserve the currently-working REAL startup service, never the mock file.
cp -a -- "$UNIT" "$BACKUP"
restore_on_error() {
  echo "FAIL: restoring prior independent dev service" >&2
  cp -a -- "$BACKUP" "$UNIT"
  systemctl daemon-reload
  systemctl restart "$SERVICE" || true
}
trap restore_on_error ERR
install -o root -g root -m 0644   "$SOURCE/systemd/ft5955-engine-dev-protocol.service" "$UNIT"
systemctl daemon-reload
systemctl restart "$SERVICE"

# Meaningful no-biometric end-to-end startup via actual protected protocol.
# No sample is sent and no MATCH can be returned in this test.
python3 -I -B - <<'PY'
import socket
with socket.socket(socket.AF_UNIX) as conn:
    conn.settimeout(90)
    conn.connect("/run/ft5955-engine-dev/engine.sock")
    conn.sendall(b"MODE E\n")
    incoming=b""
    while not incoming.endswith(b"\n") and len(incoming)<128:
        part=conn.recv(1)
        if not part: break
        incoming+=part
    if incoming != b"READY 1\n":
        raise RuntimeError("protected MOH template protocol did not initialise")
    conn.sendall(b"QUIT\n")
    incoming=b""
    while not incoming.endswith(b"\n") and len(incoming)<128:
        part=conn.recv(1)
        if not part: break
        incoming+=part
    if incoming != b"BYE\n":
        raise RuntimeError("protected MOH engine did not shut down cleanly")
print("PASS: root -> dev socket -> protected UID955 MOH template engine -> READY / BYE")
PY

touch "$MARKER"
chmod 0600 "$MARKER"
trap - ERR
echo "PASS: independent REAL MOH enrol/verify protocol installed; NO PAM."
echo "PRESERVED: original live broker, existing fprintd configuration and KDE passwords."
echo "ROLLBACK: sudo bash $0 --rollback"
