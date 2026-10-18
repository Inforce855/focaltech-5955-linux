#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Read-only KDE fingerprint/PAM and FT5955 authentication boundary preflight.
set -euo pipefail

echo "=== System identity (read-only) ==="
printf 'User: %s (UID %s)\n' "$(id -un)" "$(id -u)"
rpm -q kscreenlocker fprintd fprintd-pam || true
echo
echo "=== Authselect state ==="
authselect current
authselect check
echo
echo "=== KDE PAM entries (paths and types) ==="
for f in /etc/pam.d/kde /etc/pam.d/kde-fingerprint /etc/pam.d/fingerprint-auth /etc/pam.d/system-auth; do
  if [[ -e "$f" ]]; then
    ls -ld -- "$f"
  else
    echo "MISSING: $f"
  fi
done
echo
echo "=== Effective fingerprint PAM authentication rules ==="
grep -nE '^[[:space:]]*auth[[:space:]]' /etc/pam.d/fingerprint-auth || true
echo
echo "=== KDE fingerprint toggle (diagnostic, not authoritative proof of runtime use) ==="
if command -v kreadconfig6 >/dev/null 2>&1; then
  kreadconfig6 --file kscreenlockerrc --group Authenticators --key Fingerprint --default false
else
  echo "kreadconfig6 unavailable"
fi
echo
echo "=== Active FT5955 trial indicators ==="
systemctl show fprintd.service -p ActiveState -p FragmentPath -p DropInPaths --no-pager || true
if [[ -e /etc/systemd/system/fprintd.service.d ]]; then
  ls -la /etc/systemd/system/fprintd.service.d
fi
echo
echo "=== TRUST DECISION ==="
echo "NOT APPROVED FOR PAM: existing user-session MOH/bwrap trial is not"
echo "a privileged authentication boundary; an unkeyed template hash is not"
echo "an authenticity guarantee, and UNVERIFIED_ATTACH remains enabled."
echo "No files, packages, PAM settings or services were modified."
