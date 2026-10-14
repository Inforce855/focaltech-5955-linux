#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
# Compile and execute ONLY the repository's synthetic compatibility C tests.
# No proprietary DLL loading, USB access or fprintd integration.
set -euo pipefail
cd "$(dirname "$0")/.."

build_dir="$(mktemp -d /tmp/ft5955-native-tests.XXXXXXXX)"
trap 'rm -rf -- "$build_dir"' EXIT

# Keep the source set explicit. ft_engine.c (the PE loader) and any
# proprietary driver or engine files are intentionally excluded.
sources=(
  engine/ft5955_compat_time.c
  engine/ft5955_compat_fls.c
  engine/ft5955_compat_locale.c
  engine/ft5955_compat_datetime.c
  engine/ft5955_compat_locale_enum.c
  engine/ft5955_compat_compare.c
  engine/ft5955_compat_temp.c
  engine/ft5955_compat_cs.c
  engine/ft5955_compat_error.c
  engine/ft5955_compat_tls.c
  engine/ft5955_compat_teb_layout.c
  engine/ft5955_compat_identity.c
  engine/ft5955_compat_heap.c
  engine/ft5955_compat_sysinfo.c
  engine/ft5955_compat_env.c
  engine/ft5955_compat_slist.c
  engine/ft5955_compat_registry.c
)

shopt -s nullglob
tests=(tests/test_moh_compat_*.c)
if (("${#tests[@]}" == 0)); then
  echo "ERROR: no synthetic C tests found" >&2
  exit 2
fi

success=0
for test_source in "${tests[@]}"; do
  name="${test_source##*/}"
  name="${name%.c}"
  echo "=== BUILD AND RUN: $name ==="
  gcc -std=gnu11 -O0 -g -Wall -Wextra -Wno-unused-parameter \
    -pthread -Iengine "${sources[@]}" "$test_source" \
    -lm -latomic -o "$build_dir/$name"
  "$build_dir/$name"
  ((success+=1))
done
echo "PASS: $success synthetic C compatibility tests completed."
echo "Proprietary MOH DLL was not loaded or executed."
