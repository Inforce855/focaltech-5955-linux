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
[[ ! -e "$MARKER" && ! -L "$MARKER" ]] || {
  echo "STOP: protocol trial already marked active" >&2; exit 2;
}
# A prior failed startup restores the original unit but intentionally leaves
# its backup behind. Reuse only when the two files match byte for byte.
if [[ -e "$BACKUP" || -L "$BACKUP" ]]; then
  [[ -f "$BACKUP" && ! -L "$BACKUP" && "$(stat -c %u "$BACKUP")" == 0 ]] || {
    echo "STOP: untrusted previous unit backup" >&2; exit 2;
  }
  cmp -s "$BACKUP" "$UNIT" || {
    echo "STOP: current dev unit differs from saved backup; manual review required" >&2; exit 2;
  }
  echo "PASS: previous failed-attempt unit backup matches restored service."
fi
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
    if ! cmp -s -- "$from" "$to"; then
      if [[ "$to" == "$APP/ft5955_dev_template_launcher.py" ]]; then
        # Upgrade ONLY the exact prior faulty AST-pin parser. Refuse every
        # unrelated local change. This is not a generic overwrite operation.
        python3 -I -B - "$to" "$from" <<'PY_PIN'
from pathlib import Path
import sys
installed=Path(sys.argv[1]).read_text(encoding="utf-8")
source=Path(sys.argv[2]).read_text(encoding="utf-8")
fixed=installed.replace(
    "values=[n.value.value for node",
    "values=[node.value.value for node",
).replace(
    "except (OSError,ValueError,RuntimeError,KeyError,SyntaxError):",
    "except (OSError,ValueError,RuntimeError,KeyError,SyntaxError,AttributeError):",
)
if fixed!=source or fixed==installed:
    raise SystemExit("STOP: launcher differs beyond known AST parser fix")
PY_PIN
        install -o root -g root -m 0644 "$from" "$to"
        echo "PASS: repaired exact known launcher parser defect."
      elif [[ "$to" == "$APP/activate_ft5955_dev_protocol.sh" ]]; then
        # Previous failed attempt installed the original, root-owned installer.
        # It is safe to advance only this exact, pinned Git object version.
        [[ "$(git hash-object -- "$to")" == ab9e82774f2bc7773a83ca04d7b0b5b509f64172 ]] || {
          echo "STOP: installed installer is not the known previous version" >&2
          exit 2
        }
        install -o root -g root -m 0644 "$from" "$to"
        echo "PASS: upgraded the exact known development installer version."
      else
        echo "STOP: staged source differs; review first" >&2
        exit 2
      fi
    fi
  else
    install -o root -g root -m 0644 "$from" "$to"
  fi
}
stage "$SOURCE/driver/live-snapshot-2026-10-16/engine/template_session.c" "$STAGED/tools/ft5955_template_session.c"
for name in build_ft5955_moh_template_dev.py ft5955_dev_template_launcher.py ft5955_dev_template_gateway.py ft5955_dev_protocol_server.py ft5955_dev_relay.py ft5955_engine_broker.py activate_ft5955_dev_protocol.sh switch_ft5955_hardware_to_dev_gateway.sh run_ft5955_dev_hardware_trial.sh; do
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
  [[ -f "$APP/live-template" && ! -L "$APP/live-template" &&
     "$(stat -c %u "$APP/live-template")" == 0 &&
     "$(stat -c %g "$APP/live-template")" == "$(id -g "$ACCOUNT")" &&
     "$(stat -c %a "$APP/live-template")" == 550 ]] || {
    echo "STOP: existing protocol executable has unexpected ownership/mode" >&2; exit 2;
  }
  cmp -s "$BUILD/live-template" "$APP/live-template" || {
    echo "STOP: rebuilt protocol binary differs from previous attempt" >&2; exit 2;
  }
  echo "PASS: reused byte-identical, protected MOH template executable."
else
  install -o root -g "$ACCOUNT" -m 0550 "$BUILD/live-template" "$APP/live-template"
  cmp -s "$BUILD/live-template" "$APP/live-template" || {
    echo "STOP: binary staging mismatch" >&2; exit 2;
  }
fi

# Preserve the currently-working REAL startup service, never the mock file.
if [[ ! -e "$BACKUP" ]]; then cp -a -- "$UNIT" "$BACKUP"; fi
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
        raise RuntimeError("protected MOH template protocol did not initialise; reply="+repr(incoming[:96]))
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
echo "ROLLBACK: sudo bash /opt/ft5955-dev/run_ft5955_dev_hardware_trial.sh --stop"
