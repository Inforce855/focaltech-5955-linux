#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
# EXPERIMENTAL: real vendor DllMain + WbioQueryEngineInterface + Attach in a disposable
# bubblewrap mount/user/PID/network namespace. No USB or matching. In-memory enrolment only. Reads a user-supplied biometric PGM inside sandbox.
# API shims are incomplete. Run only after reviewing and accepting the risk.
set -euo pipefail
cd "$(dirname "$0")/.."
# Defaults to the root-owned, SHA-pinned installed DLL; explicit ZIP/DLL
# is still supported for backwards-compatible diagnostics.
source_file="${1:-/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll}"
if (( $# > 1 )) || [[ ! -f "$source_file" ]]; then
  echo "Usage: bash tools/test_moh_isolated_interactive_enroll.sh [installed.dll | 7_Fingerprint-module.zip]" >&2
  echo "Missing input: $source_file" >&2
  exit 2
fi
for command in bwrap gcc python3 objdump timeout; do
  command -v "$command" >/dev/null || { echo "Missing: $command" >&2; exit 2; }
done
root="$(mktemp -d /tmp/ft5955-isolated.XXXXXXXX)"
trap 'rm -rf -- "$root"' EXIT
chmod 700 "$root"
export FT5955_TEST_SOURCE="$(realpath "$source_file")"
export FT5955_TEST_DLL="$root/engine.dll"
python3 - <<'PY'
import os
from pathlib import Path
import tempfile
import tools.moh_engine_preflight as p
source=Path(os.environ["FT5955_TEST_SOURCE"])
dest=Path(os.environ["FT5955_TEST_DLL"])
with tempfile.TemporaryDirectory() as scratch:
    candidate=p.archive_engine(source,Path(scratch)) if source.suffix.lower()==".zip" else source
    total,libs,registered,missing=p.audit(candidate,Path("engine/ft_engine.c"))
    if total!=110 or missing:
        raise SystemExit(f"Import audit FAILED: {total} imports, {len(missing)} missing")
    import shutil, hashlib
    shutil.copyfile(candidate,dest)
    # Ensure the sandbox's actual COPY still has the pinned vendor identity
    # after the original has been audited (do not execute an altered copy).
    with dest.open("rb") as copied:
        if hashlib.file_digest(copied,"sha256").hexdigest()!=p.PIN:
            raise SystemExit("BLOCKED: temporary engine copy did not match pinned SHA-256")
dest.chmod(0o400)
print(f"Verified 5955 engine: {total}/{total} imports registered")
PY
# Compile a separate opt-in binary; leave the normal guarded build unchanged.
gcc -std=gnu11 -O0 -g -Wall -Wextra -Wno-unused-parameter \
  -DFT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT -DFT5955_ALLOW_UNVERIFIED_ATTACH \
  -DFT5955_OFFLINE_SENSOR_SIZE_SIM \
  -DFT5955_OFFLINE_SKIP_ENROLLMENT_STATUS \
  -DFT5955_OFFLINE_COMPLETION_FROM_UPDATE \
  -DFT5955_OFFLINE_SET_ENROLLMENT_PARAMETERS \
  -DFT5955_OFFLINE_PROBE_DUPLICATE \
  -DFT5955_OFFLINE_MOCK_EMPTY_QUERY_BY_CONTENT \
  -DFT5955_OFFLINE_PROBE_COMMIT \
  -DFT5955_OFFLINE_INTERACTIVE_COMPLETE_WORKFLOW \
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
  tools/moh_engine_interactive_enroll.c -lm -latomic -o "$root/interactive-enroll"
chmod 500 "$root/interactive-enroll"
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
echo "Launching isolated MOH interactive enrolment probe (20-minute session limit). No USB in engine sandbox; temporary mock-storage commit only."
echo "WARNING: experimental DLL execution; may abort or crash inside sandbox."
set +e
(
  ulimit -c 0
  timeout --signal=KILL 1200s bwrap \
    --unshare-all --die-with-parent --new-session \
    --clearenv --setenv PATH /usr/bin:/bin \
    --setenv HOME /tmp --setenv TMPDIR /tmp \
    "${mounts[@]}" \
    --proc /proc --dev /dev --tmpfs /tmp \
    --ro-bind "$root/interactive-enroll" /tmp/interactive-enroll \
    --ro-bind "$root/engine.dll" /tmp/engine.dll \
    --chdir /tmp -- /tmp/interactive-enroll --interactive-enroll /tmp/engine.dll
)
status=$?
set -e
echo "Interactive engine exit code: $status"
if [[ $status == 124 || $status == 137 ]]; then
  echo "TIMEOUT / killed."
elif [[ $status != 0 ]]; then
  echo "Synthetic probe returned an unexpected error or crashed; normal builds remain guarded."
else
  echo "Interactive enrolment session ended (temporary in-memory template wiped; nothing saved)."
fi
exit "$status"
