#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# TEMPORARY systemd service + socket isolation smoke check on Nobara.
# No MOH DLL, biometric input, fprintd invocation, PAM or permanent install.
# The only transmitted bytes are an all-zero synthetic frame.
# All test units, code and the dedicated temporary service account are removed.
set -Eeuo pipefail
umask 022
if (( EUID != 0 )) || [[ -z "${SUDO_USER:-}" || "$SUDO_USER" == root ]]; then
    echo "STOP: use sudo bash from your normal user account." >&2
    exit 2
fi
if [[ $# -ne 1 || "$1" != "--smoke" ]]; then
    echo "Usage: sudo bash $0 --smoke" >&2
    exit 2
fi
for cmd in systemctl useradd userdel getent install timeout python3 cmp; do
    command -v "$cmd" >/dev/null || { echo "STOP: missing $cmd"; exit 2; }
done
SOURCE="$(cd -- "$(dirname -- "$0")" && pwd)/ft5955_engine_broker.py"
[[ -f "$SOURCE" && ! -L "$SOURCE" ]] || {
    echo "STOP: expected broker source missing." >&2; exit 2
}
ROOT=/opt/ft5955-broker-smoke
UNIT_DIR=/etc/systemd/system
SERVICE="$UNIT_DIR/ft5955-engine-smoke.service"
SOCKET_UNIT="$UNIT_DIR/ft5955-engine-smoke.socket"
SOCKET_DIR=/run/ft5955-engine
SOCKET="$SOCKET_DIR/engine.sock"
MARK="$ROOT/FT5955_SMOKE_OWNER"
ACCOUNT=ft5955-engine
if [[ -e "$ROOT" || -L "$ROOT" || -e "$SERVICE" || -L "$SERVICE" ||
      -e "$SOCKET_UNIT" || -L "$SOCKET_UNIT" || -e "$SOCKET_DIR" ||
      -L "$SOCKET_DIR" ]] || getent passwd "$ACCOUNT" >/dev/null; then
    echo "STOP: existing FT5955 broker resources/account detected; won't touch them." >&2
    exit 2
fi
if [[ -e /etc/systemd/system/ft5955-engine.service ||
      -e /etc/systemd/system/ft5955-engine.socket ||
      -e /opt/ft5955-system-trial/engine ]]; then
    echo "STOP: other engine integration already exists; inspect before smoke test." >&2
    exit 2
fi
# No change whatsoever to the existing fprintd unit/drop-ins.
if systemctl is-active --quiet ft5955-engine-smoke.service ||
   systemctl is-active --quiet ft5955-engine-smoke.socket; then
    echo "STOP: a broker smoke unit is already active." >&2
    exit 2
fi

installed=0
account_created=0
cleanup() {
    local rc=$?
    trap - EXIT ERR
    if (( installed )); then
        systemctl stop ft5955-engine-smoke.socket ft5955-engine-smoke.service >/dev/null 2>&1 || true
        # Remove only files installed by this one-run trial. A root-owned
        # directory prevents any non-root process modifying these.
        if [[ -f "$MARK" && ! -L "$MARK" && "$(cat "$MARK")" == FT5955_BROKER_SMOKE_V1 ]]; then
            rm -f -- "$SERVICE" "$SOCKET_UNIT"
            systemctl daemon-reload || true
            rm -f -- "$ROOT/ft5955_engine_broker.py" "$ROOT/mock_gateway.py" "$MARK"
            rmdir -- "$ROOT" 2>/dev/null || true
            rmdir -- "$SOCKET_DIR" 2>/dev/null || true
        else
            echo "WARNING: smoke marker altered: inspect systemd units manually" >&2
        fi
    fi
    if (( account_created )); then
        userdel "$ACCOUNT" || echo "WARNING: could not remove temporary service account." >&2
    fi
    if (( installed )); then
        if [[ ! -e "$SERVICE" && ! -e "$SOCKET_UNIT" &&
              ! -e "$ROOT" && ! -e "$SOCKET_DIR" ]]; then
            echo "PASS: temporary broker unit files, sandbox code, socket and account removed."
        else
            echo "WARNING: broker smoke cleanup incomplete, review before further testing." >&2
        fi
    fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 1' ERR

install -d -m 0755 -o root -g root "$ROOT"
printf '%s\n' FT5955_BROKER_SMOKE_V1 > "$MARK"
installed=1
install -m 0644 -o root -g root "$SOURCE" "$ROOT/ft5955_engine_broker.py"
cat > "$ROOT/mock_gateway.py" <<'PY'
#!/usr/bin/env python3
# Synthetic transport ONLY. Cannot produce a biometric MATCH.
import argparse, sys
parser = argparse.ArgumentParser()
parser.add_argument("--moh-dir", required=True)
parser.parse_args()
reader, writer = sys.stdin.buffer, sys.stdout.buffer
assert reader.readline() == b"MODE E\n"
writer.write(b"READY 1\n"); writer.flush()
assert reader.readline() == b"FRAME\n"
data = reader.read(5120)
assert len(data) == 5120 and not any(data)
writer.write(b"RETRY QUALITY\n"); writer.flush()
assert reader.readline() == b"QUIT\n"
writer.write(b"BYE\n"); writer.flush()
PY
chmod 0644 "$ROOT/mock_gateway.py"
# No login shell, password, home creation, or system authentication module.
useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin "$ACCOUNT"
account_created=1
cat > "$SOCKET_UNIT" <<'UNIT'
[Unit]
Description=FT5955 synthetic-only MOH broker socket smoke trial
[Socket]
ListenStream=/run/ft5955-engine/engine.sock
SocketUser=ft5955-engine
SocketGroup=root
SocketMode=0660
DirectoryMode=0755
RemoveOnStop=yes
[Install]
WantedBy=sockets.target
UNIT
cat > "$SERVICE" <<'UNIT'
[Unit]
Description=FT5955 non-root synthetic-only broker smoke trial
Requires=ft5955-engine-smoke.socket
After=ft5955-engine-smoke.socket
[Service]
Type=simple
User=ft5955-engine
Group=ft5955-engine
ExecStart=/usr/bin/python3 /opt/ft5955-broker-smoke/ft5955_engine_broker.py --serve --gateway /opt/ft5955-broker-smoke/mock_gateway.py --moh-dir /opt/ft5955-broker-smoke
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectHome=yes
ProtectSystem=strict
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
CapabilityBoundingSet=
AmbientCapabilities=
RestrictAddressFamilies=AF_UNIX
RestrictSUIDSGID=yes
LockPersonality=yes
IPAddressDeny=any
TimeoutStopSec=10
UNIT
echo "Starting ONLY temporary synthetic broker socket/service (not fprintd)."
systemctl daemon-reload
systemctl start ft5955-engine-smoke.socket
# This local root synthetic client is allowed by SO_PEERCRED; it does not
# call normal fprintd or any authentication mechanism.
timeout 20s python3 - <<'PY'
import socket
import time
from pathlib import Path
path = "/run/ft5955-engine/engine.sock"
end = time.monotonic() + 8
while not Path(path).exists():
    if time.monotonic() >= end:
        raise RuntimeError("Broker socket not created")
    time.sleep(0.05)
client = socket.socket(socket.AF_UNIX)
client.settimeout(12)
client.connect(path)
client.sendall(b"MODE E\nFRAME\n" + bytes(5120) + b"QUIT\n")
client.shutdown(socket.SHUT_WR)
received = bytearray()
while True:
    part = client.recv(8192)
    if not part:
        break
    received.extend(part)
client.close()
expected = b"READY 1\nRETRY QUALITY\nBYE\n"
if bytes(received) != expected:
    raise RuntimeError("Wrong mock reply (NO biometric matching tested)")
print("PASS: non-root systemd service, protected UNIX socket, root-only peer")
print("PASS: synthetic MODE E -> READY 1 -> RETRY QUALITY -> BYE")
print("PASS: no vendor DLL, USB, fingerprints, normal fprintd, PAM or KDE changes")
PY
PID="$(systemctl show ft5955-engine-smoke.service --value -p MainPID)"
if [[ ! "$PID" =~ ^[0-9]+$ || "$PID" -le 1 ]]; then
    echo "STOP: broker systemd service missing MainPID!" >&2
    exit 1
fi
UID_ON_HOST="$(stat -c %u "/proc/$PID")"
EXPECTED_UID="$(id -u "$ACCOUNT")"
[[ "$UID_ON_HOST" == "$EXPECTED_UID" ]] || {
    echo "STOP: broker process didn't run as dedicated non-root UID" >&2
    exit 1
}
echo "PASS: isolated broker PID $PID is non-root UID $EXPECTED_UID."
echo "PASS: temporary service trial complete, cleaning up automatically."
