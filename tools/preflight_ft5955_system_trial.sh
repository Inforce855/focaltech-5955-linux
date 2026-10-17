#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Read-only Nobara/Fedora system fprintd integration preflight.
# No sudo, USB access, service start/stop, enrolment, file modifications,
# PAM edits, fingerprint storage access or systemd reload.
set -euo pipefail

if (( EUID == 0 )); then
  echo "STOP: run as your ordinary user, NEVER with sudo." >&2
  exit 2
fi
if [[ ! -r /etc/os-release ]]; then
  echo "STOP: cannot inspect Linux distribution." >&2
  exit 2
fi
if ! command -v systemctl >/dev/null || ! command -v rpm >/dev/null; then
  echo "STOP: this preflight expects systemd and RPM (Nobara/Fedora)." >&2
  exit 2
fi

printf '%s\n' '=== FT5955 REVERSIBLE SYSTEM TRIAL — READ-ONLY PREFLIGHT ==='
printf '%s\n' 'No services or files will be changed. No biometric operations.'
printf '%s\n' '=== OS ==='
# Basic distro/version names only; no machine identifiers or serial numbers.
(
  . /etc/os-release
  printf 'ID=%s\nVERSION_ID=%s\nID_LIKE=%s\n' "${ID:-?}" "${VERSION_ID:-?}" "${ID_LIKE:-?}"
)

printf '%s\n' '=== RELEVANT RPM PACKAGES ==='
for p in fprintd libfprint fprintd-pam libfprint-devel; do
  rpm -q --qf '%{NAME} %{VERSION}-%{RELEASE}\n' "$p" 2>/dev/null ||
    printf '%s is not installed\n' "$p"
done
printf '%s\n' '=== SYSTEM FPRINTD UNIT ==='
# 'show' does not start service. Print only selected service properties;
# deliberately omit Environment/EnvironmentFiles and stored fingerprints.
systemctl show fprintd.service --no-pager \
    -p LoadState -p FragmentPath -p DropInPaths \
    -p ActiveState -p SubState -p UnitFileState \
    -p Type -p BusName -p User -p Group \
    -p ExecStart -p MainPID -p StateDirectory \
    -p ProtectHome -p ProtectSystem -p PrivateTmp \
    -p NoNewPrivileges -p MemoryDenyWriteExecute \
    -p DevicePolicy -p DeviceAllow \
    -p RestrictAddressFamilies || true

printf '%s\n' '=== SERVICE FILE PATHS (NO CONTENT DUMP) ==='
for file in /usr/lib/systemd/system/fprintd.service \
            /etc/systemd/system/fprintd.service \
            /etc/systemd/system/fprintd.service.d \
            /run/systemd/system/fprintd.service.d \
            /usr/libexec/fprintd \
            /usr/lib64/libfprint-2.so.2; do
  if [[ -e "$file" ]]; then
    ls -ld -- "$file"
  else
    printf 'NOT PRESENT: %s\n' "$file"
  fi
done

printf '%s\n' '=== LIBFPRINT LINK RESOLUTION ==='
if [[ -e /usr/lib64/libfprint-2.so.2 ]]; then
  readlink -f -- /usr/lib64/libfprint-2.so.2
else
  echo 'No libfprint-2.so.2 in standard lib64 path'
fi

printf '%s\n' '=== DRIVER TEST SOURCE ==='
repo="$HOME/Projects/ft5955-independent-build-check"
if [[ -f "$repo/tools/verify_ft5955_clean_clone.py" ]]; then
  printf 'YES: separate clean-build checkout exists\n'
else
  printf 'NOT FOUND: expected separate clean-build checkout\n'
fi
printf '%s\n' '=== PRE-FLIGHT COMPLETE (READ-ONLY) ==='
printf '%s\n' 'Do NOT use sudo with any FT5955 Python builder or enable fingerprint PAM yet.'
