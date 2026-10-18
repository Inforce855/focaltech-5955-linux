#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Explicit DEV-only mock -> real startup probe switching, with rollback.
# Does not affect live /run/ft5955-engine, fprintd or PAM.
set -Eeuo pipefail
umask 077
[[ $# == 1 && ( "$1" == --activate || "$1" == --rollback || "$1" == --status ) ]] || { echo "Usage: sudo bash $0 --activate|--rollback|--status" >&2; exit 2; }
[[ $EUID == 0 ]] || { echo "STOP: sudo required" >&2; exit 2; }
MODE="$1"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DEV=/opt/ft5955-dev
UNIT=/etc/systemd/system/ft5955-engine-dev.service
ORIGINAL="$DEV/ft5955_dev_mock_server.py"
PROBE="$DEV/ft5955_dev_real_startup_server.py"
MARKER="$DEV/.real-startup-probe-enabled"
[[ -f "$UNIT" && ! -L "$UNIT" && -f "$ORIGINAL" && ! -L "$ORIGINAL" ]] || { echo "STOP: normal dev baseline missing" >&2; exit 2; }
if [[ "$MODE" == --status ]]; then
  grep '^ExecStart=' "$UNIT"
  systemctl show ft5955-engine-dev.service -p ActiveState -p User -p Group
  [[ -f "$MARKER" ]] && echo "Real startup probe selected" || echo "Original synthetic mock selected"
  exit 0
fi
if [[ "$MODE" == --activate ]]; then
  [[ ! -e "$PROBE" && ! -L "$PROBE" && ! -e "$MARKER" && ! -L "$MARKER" ]] || { echo "STOP: probe already staged" >&2; exit 2; }
  [[ -f "$SOURCE_DIR/tools/ft5955_dev_real_startup_server.py" ]] || { echo "STOP: probe source missing" >&2; exit 2; }
  [[ -f "$DEV/live-identify" && ! -L "$DEV/live-identify" ]] || { echo "STOP: staged compiled ELF missing" >&2; exit 2; }
  [[ "$(sha256sum "$DEV/live-identify" | cut -d' ' -f1)" == 3440b0316340af62b0872e7cd61bb412b6ecd921679d1b0d503d72455779feb4 ]] || { echo "STOP: compiled binary hash mismatch" >&2; exit 2; }
  grep -Fxq 'ExecStart=/usr/bin/python3 -B /opt/ft5955-dev/ft5955_dev_mock_server.py' "$UNIT" || { echo "STOP: unexpected dev service" >&2; exit 2; }
  python3 - <<PY
import ast
from pathlib import Path
ast.parse(Path("$SOURCE_DIR/tools/ft5955_dev_real_startup_server.py").read_text())
PY
  install -m 0644 -o root -g root "$SOURCE_DIR/tools/ft5955_dev_real_startup_server.py" "$PROBE"
  sed -i 's@/opt/ft5955-dev/ft5955_dev_mock_server.py@/opt/ft5955-dev/ft5955_dev_real_startup_server.py@' "$UNIT"
  touch "$MARKER"; chmod 0600 "$MARKER"
  systemctl daemon-reload
  systemctl restart ft5955-engine-dev.service
  echo "PASS: DEV real startup probe selected; every socket reply still denies auth."
else
  [[ -f "$MARKER" && ! -L "$MARKER" && -f "$PROBE" && ! -L "$PROBE" ]] || { echo "STOP: no known probe activation to roll back" >&2; exit 2; }
  grep -Fxq 'ExecStart=/usr/bin/python3 -B /opt/ft5955-dev/ft5955_dev_real_startup_server.py' "$UNIT" || { echo "STOP: dev service differs; manual review required" >&2; exit 2; }
  sed -i 's@/opt/ft5955-dev/ft5955_dev_real_startup_server.py@/opt/ft5955-dev/ft5955_dev_mock_server.py@' "$UNIT"
  systemctl daemon-reload
  systemctl restart ft5955-engine-dev.service
  rm -- "$PROBE" "$MARKER"
  echo "PASS: original DEV synthetic mock restored."
fi
