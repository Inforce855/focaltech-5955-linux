#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# One guarded entry point for the isolated real-MOH hardware evaluation.
# PAM/login/authselect/SDDM/sudo authentication are NEVER configured.
set -Eeuo pipefail
[[ $# -eq 1 && ( "$1" == --start || "$1" == --stop || "$1" == --status ) ]] || {
  echo "Usage: sudo bash $0 --start|--stop|--status" >&2; exit 2;
}
[[ $EUID -eq 0 ]] || { echo "STOP: sudo required" >&2; exit 2; }
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
PROTOCOL="$HERE/activate_ft5955_dev_protocol.sh"
ROUTING="$HERE/switch_ft5955_hardware_to_dev_gateway.sh"
[[ -f "$PROTOCOL" && -f "$ROUTING" && ! -L "$PROTOCOL" && ! -L "$ROUTING" ]] || {
  echo "STOP: required guarded installers missing" >&2; exit 2;
}
if [[ "$1" == --status ]]; then
  bash "$PROTOCOL" --status
  bash "$ROUTING" --status
  exit 0
fi
if [[ "$1" == --stop ]]; then
  # Remove fprintd routing before stopping the protected service.
  if [[ -f /opt/ft5955-dev/.hw-dev-gateway-enabled ]]; then
    bash "$ROUTING" --rollback
  fi
  if [[ -f /opt/ft5955-dev/.template-protocol-enabled ]]; then
    bash "$PROTOCOL" --rollback
  fi
  echo "PASS: protected hardware trial rolled back; original user trial retained."
  exit 0
fi
[[ ! -e /opt/ft5955-dev/.template-protocol-enabled &&
   ! -e /opt/ft5955-dev/.hw-dev-gateway-enabled ]] || {
  echo "STOP: development hardware trial already active or partially activated" >&2; exit 2;
}
echo "=== Building and starting protected UID955 real template engine ==="
bash "$PROTOCOL" --activate
echo "=== Switching ONLY existing experimental fprintd gateway ==="
if ! bash "$ROUTING" --activate; then
  echo "FAIL: fprintd route switch failed; restoring original dev service" >&2
  bash "$PROTOCOL" --rollback || true
  exit 1
fi
echo "PASS: protected real-MOH hardware trial active (NO PAM)."
echo "Run once as ordinary user: fprintd-verify"
echo "Stop safely: sudo bash $0 --stop"
