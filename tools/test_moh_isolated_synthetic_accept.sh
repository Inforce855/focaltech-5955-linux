#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
# EXPERIMENTAL: real vendor DllMain + WbioQueryEngineInterface + Attach in a disposable
# bubblewrap mount/user/PID/network namespace. NO USB or biometrics. Attach may invoke incomplete shims.
# API shims are incomplete. Run only after reviewing and accepting the risk.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -lt 1 || $# -gt 2 || ! -f "$1" || ( $# -eq 2 && "$2" != "gradient" && "$2" != "waves" ) ]]; then
  echo "Usage: bash tools/test_moh_isolated_synthetic_accept.sh /path/to/7_Fingerprint-module.zip [gradient|waves]" >&2
  exit 2
fi
for command in bwrap gcc python3 objdump timeout; do
  command -v "$command" >/dev/null || { echo "Missing: $command" >&2; exit 2; }
done
pattern="${2:-gradient}"
root="$(mktemp -d /tmp/ft5955-isolated.XXXXXXXX)"
trap 'rm -rf -- "$root"' EXIT
chmod 700 "$root"
export FT5955_TEST_ARCHIVE="$(realpath "$1")"
export FT5955_TEST_DLL="$root/engine.dll"
python3 - <<'PY'
import os
from pathlib import Path
import tempfile
import tools.moh_engine_preflight as p
archive=Path(os.environ["FT5955_TEST_ARCHIVE"])
dest=Path(os.environ["FT5955_TEST_DLL"])
with tempfile.TemporaryDirectory() as scratch:
    candidate=p.archive_engine(archive,Path(scratch)) if archive.suffix.lower()==".zip" else archive
    total,libs,registered,missing=p.audit(candidate,Path("engine/ft_engine.c"))
    if total!=110 or missing:
        raise SystemExit(f"Import audit FAILED: {total} imports, {len(missing)} missing")
    import shutil
    shutil.copyfile(candidate,dest)
dest.chmod(0o400)
print(f"Verified 5955 engine: {total}/{total} imports registered")
PY
# Compile a separate opt-in binary; leave the normal guarded build unchanged.
gcc -std=gnu11 -O0 -g -Wall -Wextra -Wno-unused-parameter \
  -DFT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT -DFT5955_ALLOW_UNVERIFIED_ATTACH \
  -DFT5955_OFFLINE_SENSOR_SIZE_SIM \
  -pthread -Iengine engine/ft_engine.c engine/ft5955_compat_time.c \
  engine/ft5955_compat_fls.c engine/ft5955_compat_locale.c \
  engine/ft5955_compat_datetime.c engine/ft5955_compat_locale_enum.c \
  engine/ft5955_compat_compare.c engine/ft5955_compat_temp.c \
  engine/ft5955_compat_cs.c engine/ft5955_compat_error.c \
  engine/ft5955_compat_tls.c engine/ft5955_compat_teb_layout.c \
  engine/ft5955_compat_identity.c engine/ft5955_compat_heap.c \
  engine/ft5955_compat_sysinfo.c engine/ft5955_compat_env.c \
  engine/ft5955_compat_slist.c engine/ft5955_compat_registry.c \
  engine/ft5955_pe_guard.c engine/ft5955_pe_exports.c \
  tools/moh_engine_synthetic_accept.c -lm -latomic -o "$root/synthetic-accept"
chmod 500 "$root/synthetic-accept"
# Build a minimal userspace view. All libraries come from host in readonly
# mounts. No /home, real /dev, writable host path or network is accessible.
mounts=(--ro-bind /usr /usr)
for path in /lib /lib64 /bin /sbin; do
  if [[ -L "$path" ]]; then
    target="$(readlink "$path")"
    if [[ "$target" == /* ]]; then
      echo "Absolute system symlink $path -> $target unsupported by probe" >&2
      exit 2
    fi
    mounts+=(--symlink "$target" "$path")
  elif [[ -d "$path" ]]; then
    mounts+=(--ro-bind "$path" "$path")
  fi
done
echo "Launching isolated MOH DllMain/Attach/synthetic AcceptSampleData probe (15-second limit)."
echo "WARNING: experimental DLL execution; may abort or crash inside sandbox."
set +e
(
  ulimit -c 0
  timeout --signal=KILL 15s bwrap \
    --unshare-all --die-with-parent --new-session \
    --clearenv --setenv PATH /usr/bin:/bin \
    --setenv HOME /tmp --setenv TMPDIR /tmp \
    "${mounts[@]}" \
    --proc /proc --dev /dev --tmpfs /tmp \
    --ro-bind "$root/synthetic-accept" /tmp/synthetic-accept \
    --ro-bind "$root/engine.dll" /tmp/engine.dll \
    --chdir /tmp -- /tmp/synthetic-accept --synthetic-accept /tmp/engine.dll "$pattern"
)
status=$?
set -e
echo "Isolated Synthetic Accept probe exit code: $status"
if [[ $status == 124 || $status == 137 ]]; then
  echo "TIMEOUT / killed."
elif [[ $status != 0 ]]; then
  echo "Synthetic probe returned an unexpected error or crashed; normal builds remain guarded."
else
  echo "Synthetic AcceptSampleData returned HRESULT 0 (NOT proof of matching)."
fi
exit "$status"
