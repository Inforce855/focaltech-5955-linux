#!/usr/bin/env bash
# Standalone source-only build in existing private libfprint test directory.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
SRC="${FT5955_LIBFPRINT_SRC:-$HOME/Projects/libfprint-ft5955}"
BUILD="${FT5955_LIBFPRINT_BUILD:-$SRC/build-ft5955}"
[[ $(id -u) -ne 0 ]] || { echo 'STOP: never use sudo.' >&2; exit 2; }
[[ -f tests/native_verify_safety_v094.c ]] || { echo 'Missing v0.9.4 C source' >&2; exit 2; }
[[ -f tests/ft5955_quality_proxy_v094.py ]] || { echo 'Missing v0.9.4 proxy' >&2; exit 2; }
[[ -f "$SRC/libfprint/fprint.h" ]] || { echo 'Missing private libfprint header' >&2; exit 2; }
[[ -f "$BUILD/libfprint/libfprint-2.so.2" ]] || { echo 'Missing private libfprint' >&2; exit 2; }
python3 -m py_compile tests/ft5955_quality_proxy_v094.py
for dep in glib-2.0 gio-2.0 gobject-2.0; do pkg-config --exists "$dep"; done
mkdir -p build-tests
# shellcheck disable=SC2046
cc -std=gnu11 -Wall -Wextra -Werror -O2 \
  -I "$SRC/libfprint" -I "$BUILD/libfprint" \
  $(pkg-config --cflags glib-2.0 gio-2.0 gobject-2.0) \
  tests/native_verify_safety_v094.c -L "$BUILD/libfprint" \
  -Wl,-rpath,"$BUILD/libfprint" -lfprint-2 \
  $(pkg-config --libs glib-2.0 gio-2.0 gobject-2.0) \
  -o build-tests/native_verify_safety_v094
if ! ldd build-tests/native_verify_safety_v094 | grep -F "$BUILD/libfprint/libfprint-2.so.2"; then
  rm -f build-tests/native_verify_safety_v094
  echo 'STOP: executable did not link to PRIVATE libfprint' >&2
  exit 3
fi
echo 'PASS: v0.9.4 compiled against private libfprint; no system installation.'
