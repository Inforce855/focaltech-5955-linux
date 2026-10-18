#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Explicit temporary hardware trial: route existing experimental fprintd
# through the ROOT-only relay and separate real UID955 MOH dev service.
# Never touches PAM, authselect, SDDM, sudo or enrolled fingerprint files.
set -Eeuo pipefail
umask 077
[[ $# -eq 1 && ( "$1" == --activate || "$1" == --rollback || "$1" == --status ) ]] || {
  echo "Usage: sudo bash $0 --activate|--rollback|--status" >&2; exit 2;
}
[[ $EUID -eq 0 ]] || { echo "STOP: sudo required" >&2; exit 2; }
MODE="$1"
DEV=/opt/ft5955-dev
MARK="$DEV/.hw-dev-gateway-enabled"
DROP=/etc/systemd/system/fprintd.service.d/95-ft5955-moh-dev-gateway.conf
BASE=/etc/systemd/system/fprintd.service.d/90-ft5955-system-trial.conf
RELAY="$DEV/ft5955_dev_relay.py"
SOCKET=/run/ft5955-engine-dev/engine.sock
expected() {
cat <<'EOF'
# FT5955 TEMPORARY: root fprintd -> protected UID955 MOH DEV service
# No login/PAM integration; preserves original experimental fprintd library.
[Service]
Environment=FT5955_ENGINE_GATEWAY=/opt/ft5955-dev/ft5955_dev_relay.py
EOF
}
if [[ "$MODE" == --status ]]; then
  systemctl show fprintd.service -p Environment -p ActiveState --no-pager
  if [[ -f "$MARK" ]]; then echo "DEV hardware routing marked active"; else echo "DEV hardware routing not marked active"; fi
  exit 0
fi
if [[ "$MODE" == --rollback ]]; then
  [[ -f "$MARK" && ! -L "$MARK" && -f "$DROP" && ! -L "$DROP" ]] || {
    echo "STOP: known route marker/drop-in absent" >&2; exit 2;
  }
  cmp -s <(expected) "$DROP" || {
    echo "STOP: development routing override differs; manual review required" >&2; exit 2;
  }
  rm -- "$DROP"
  systemctl daemon-reload
  systemctl restart fprintd.service
  rm -- "$MARK"
  echo "PASS: previous fprintd gateway routing restored; no PAM changes."
  exit 0
fi

[[ ! -e "$MARK" && ! -L "$MARK" && ! -e "$DROP" && ! -L "$DROP" ]] || {
  echo "STOP: previous/unknown hardware routing exists; no overwrite" >&2; exit 2;
}
[[ -f "$DEV/.template-protocol-enabled" && -f "$RELAY" && ! -L "$RELAY" &&
   "$(stat -c %u "$RELAY")" == 0 && -S "$SOCKET" && ! -L "$SOCKET" ]] || {
  echo "STOP: dedicated real MOH protocol service not installed and ready" >&2; exit 2;
}
[[ "$(systemctl is-active ft5955-engine-dev.service)" == active ]] || {
  echo "STOP: dedicated MOH development service inactive" >&2; exit 2;
}
grep -Fq 'ft5955_dev_protocol_server.py' /etc/systemd/system/ft5955-engine-dev.service || {
  echo "STOP: expected protected protocol server not configured" >&2; exit 2;
}
[[ -f "$BASE" && ! -L "$BASE" ]] || {
  echo "STOP: previous known fprintd laboratory configuration is absent" >&2; exit 2;
}
grep -Fxq 'Environment=FT5955_EXPERIMENTAL_ENABLE=1' "$BASE" || {
  echo "STOP: no existing enabled experimental driver to route" >&2; exit 2;
}
grep -Fxq 'Environment=LD_LIBRARY_PATH=/opt/ft5955-system-trial/lib' "$BASE" || {
  echo "STOP: original staged driver path differs" >&2; exit 2;
}
[[ -d /etc/systemd/system/fprintd.service.d && ! -L /etc/systemd/system/fprintd.service.d ]] || {
  echo "STOP: unexpected fprintd override directory" >&2; exit 2;
}
if rpm -q fprintd-pam >/dev/null 2>&1; then
  echo "STOP: fprintd-pam installed, refusing laboratory gateway switch" >&2; exit 2;
fi
expected > "$DROP"
chmod 0644 "$DROP"
restore_on_failure() {
  echo "FAIL: restoring the original live user-session gateway" >&2
  rm -f -- "$DROP"
  systemctl daemon-reload
  systemctl restart fprintd.service || true
}
trap restore_on_failure ERR
systemctl daemon-reload
systemctl restart fprintd.service
ENVIRONMENT="$(systemctl show fprintd.service -p Environment --value)"
[[ "$ENVIRONMENT" == *"FT5955_ENGINE_GATEWAY=$RELAY"* ]] || {
  echo "STOP: dev relay not selected in effective fprintd environment" >&2; false;
}
[[ "$(systemctl is-active fprintd.service)" == active ]] || {
  echo "STOP: fprintd failed to restart" >&2; false;
}
touch "$MARK"
chmod 0600 "$MARK"
trap - ERR
echo "PASS: existing real fprintd now routes to protected MOH UID955 dev service."
echo "No fingerprints scanned; PAM and password unlock untouched."
echo "HARDWARE TEST: fprintd-verify"
echo "RESTORE: sudo bash $0 --rollback"
