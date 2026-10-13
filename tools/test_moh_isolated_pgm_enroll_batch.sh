#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
# EXPERIMENTAL: real vendor DllMain + WbioQueryEngineInterface + Attach in a disposable
# bubblewrap mount/user/PID/network namespace. No USB or matching. In-memory enrolment only. Reads a user-supplied biometric PGM inside sandbox.
# API shims are incomplete. Run only after reviewing and accepting the risk.
set -euo pipefail
cd "$(dirname "$0")/.."
# Optional, strictly offline comparison: invoke the standard WinBio V3
# SetEnrollmentParameters callback after CreateEnrollment.
declare -a enrollment_setup_flags=()
input_kind=pgm
windows_bir_mode=none
completion_from_update=0
probe_commit=0
skip_status=0
duplicate_check=0
mock_content_query=0
verify_after_commit=0
while (( $# > 0 )); do
  case "$1" in
    --windows-bir-direct)
      [[ "$windows_bir_mode" == none ]] || { echo 'Choose one Windows BIR mode only' >&2; exit 2; }
      input_kind=bir
      windows_bir_mode=direct
      enrollment_setup_flags+=(-DFT5955_OFFLINE_WINDOWS_BIR_DIRECT)
      shift ;;
    --windows-bir-synthetic)
      [[ "$windows_bir_mode" == none ]] || { echo 'Choose one Windows BIR mode only' >&2; exit 2; }
      input_kind=bir
      windows_bir_mode=synthetic
      enrollment_setup_flags+=(-DFT5955_OFFLINE_WINDOWS_BIR_SYNTHETIC)
      shift ;;
    --completion-from-update)
      completion_from_update=1
      enrollment_setup_flags+=(-DFT5955_OFFLINE_COMPLETION_FROM_UPDATE)
      shift ;;
    --skip-enrollment-status)
      skip_status=1
      enrollment_setup_flags+=(-DFT5955_OFFLINE_SKIP_ENROLLMENT_STATUS)
      shift ;;
    --probe-commit-in-memory)
      probe_commit=1
      enrollment_setup_flags+=(-DFT5955_OFFLINE_PROBE_COMMIT)
      shift ;;
    --with-duplicate-check)
      duplicate_check=1
      enrollment_setup_flags+=(-DFT5955_OFFLINE_PROBE_DUPLICATE)
      shift ;;
    --mock-empty-content-query)
      mock_content_query=1
      enrollment_setup_flags+=(-DFT5955_OFFLINE_MOCK_EMPTY_QUERY_BY_CONTENT)
      shift ;;
    --verify-after-commit)
      verify_after_commit=1
      enrollment_setup_flags+=(-DFT5955_OFFLINE_VERIFY_AFTER_COMMIT)
      shift ;;
    --invert-pixels)
      enrollment_setup_flags+=(-DFT5955_OFFLINE_INVERT_INPUT_PIXELS)
      shift ;;
    --with-enrollment-parameters)
      enrollment_setup_flags+=(-DFT5955_OFFLINE_SET_ENROLLMENT_PARAMETERS)
      shift ;;
    --with-extended-status)
      enrollment_setup_flags+=(-DFT5955_OFFLINE_QUERY_EXTENDED_ENROLLMENT_STATUS)
      shift ;;
    --with-sample-hint)
      enrollment_setup_flags+=(-DFT5955_OFFLINE_QUERY_SAMPLE_HINT)
      shift ;;
    *) break ;;
  esac
done
if (( $# < 2 || $# > 21 )); then
  echo "Usage: bash tools/test_moh_isolated_pgm_enroll_batch.sh [--windows-bir-direct|--windows-bir-synthetic] [--invert-pixels] [--completion-from-update] [--skip-enrollment-status] [--probe-commit-in-memory] [--with-duplicate-check] [--mock-empty-content-query] [--verify-after-commit] [--with-enrollment-parameters] [--with-extended-status] [--with-sample-hint] vendor.zip sample1.pgm [...], or vendor.zip one_private.bir" >&2
  exit 2
fi
if [[ ! -f "$1" ]]; then
  echo "ERROR: Vendor driver archive not found: $1" >&2
  exit 2
fi
if (( (skip_status || probe_commit) && ! completion_from_update )); then
  echo "ERROR: --probe-commit-in-memory and --skip-enrollment-status require --completion-from-update." >&2
  exit 2
fi
if (( verify_after_commit && (!probe_commit || !duplicate_check || !mock_content_query || !skip_status || !completion_from_update) )); then
  echo "ERROR: --verify-after-commit requires --probe-commit-in-memory --with-duplicate-check --mock-empty-content-query --skip-enrollment-status --completion-from-update." >&2
  exit 2
fi
if (( mock_content_query && ! duplicate_check )); then
  echo "ERROR: --mock-empty-content-query requires --with-duplicate-check." >&2
  exit 2
fi
if (( duplicate_check && ! probe_commit )); then
  echo "ERROR: --with-duplicate-check requires --probe-commit-in-memory." >&2
  exit 2
fi
if [[ "$input_kind" == bir && "$probe_commit" == 1 ]]; then
  echo "ERROR: cannot probe commit from a single Windows BIR capture." >&2
  exit 2
fi
if [[ "$input_kind" == bir ]]; then
  if (( $# != 2 )); then
    echo "ERROR: Windows BIR A/B run requires exactly one private BIR input." >&2
    exit 2
  fi
  if [[ " ${enrollment_setup_flags[*]} " == *" -DFT5955_OFFLINE_INVERT_INPUT_PIXELS "* ]]; then
    echo "ERROR: BIR polarity cannot be modified in the raw BIR A/B test." >&2
    exit 2
  fi
fi
declare -a sample_mounts=() sample_paths=()
declare -A seen=()
index=0
for arg in "${@:2}"; do
  if [[ ! -f "$arg" ]]; then
    echo "ERROR: PGM image not found: $arg" >&2
    exit 2
  fi
  if [[ "$input_kind" == bir && "$arg" != *.bir ]]; then
    echo "ERROR: the Windows reference must be a .bir file." >&2
    exit 2
  fi
  original="$(realpath -- "$arg")"
  if [[ -n "${seen[$original]:-}" ]]; then
    echo "ERROR: duplicate PGM supplied; use distinct capture files" >&2
    exit 2
  fi
  seen[$original]=1
  sample_mounts+=(--ro-bind "$original" "/tmp/sample$index.$input_kind")
  sample_paths+=("/tmp/sample$index.$input_kind")
  ((index+=1))
done
for command in bwrap gcc python3 objdump timeout; do
  command -v "$command" >/dev/null || { echo "Missing: $command" >&2; exit 2; }
done
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
  -pthread "${enrollment_setup_flags[@]}" -Iengine engine/ft_engine.c engine/ft5955_compat_time.c \
  engine/ft5955_compat_fls.c engine/ft5955_compat_locale.c \
  engine/ft5955_compat_datetime.c engine/ft5955_compat_locale_enum.c \
  engine/ft5955_compat_compare.c engine/ft5955_compat_temp.c \
  engine/ft5955_compat_cs.c engine/ft5955_compat_error.c \
  engine/ft5955_compat_tls.c engine/ft5955_compat_teb_layout.c \
  engine/ft5955_compat_identity.c engine/ft5955_compat_heap.c \
  engine/ft5955_compat_sysinfo.c engine/ft5955_compat_env.c \
  engine/ft5955_compat_slist.c engine/ft5955_compat_registry.c \
  engine/ft5955_pe_guard.c engine/ft5955_pe_exports.c \
  tools/moh_engine_pgm_enroll_batch.c -lm -latomic -o "$root/pgm-enroll-batch"
chmod 500 "$root/pgm-enroll-batch"
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
echo "Launching isolated MOH enrolment probe (15-second limit). No USB, no persistent template."
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
    --ro-bind "$root/pgm-enroll-batch" /tmp/pgm-enroll-batch \
    --ro-bind "$root/engine.dll" /tmp/engine.dll \
    "${sample_mounts[@]}" \
    --chdir /tmp -- /tmp/pgm-enroll-batch --pgm-enroll-batch /tmp/engine.dll "${sample_paths[@]}"
)
status=$?
set -e
echo "Isolated PGM Accept probe exit code: $status"
if [[ $status == 124 || $status == 137 ]]; then
  echo "TIMEOUT / killed."
elif [[ $status != 0 ]]; then
  echo "Synthetic probe returned an unexpected error or crashed; normal builds remain guarded."
else
  echo "Multi-sample enrolment diagnostic returned (no template persisted or saved)."
fi
exit "$status"
