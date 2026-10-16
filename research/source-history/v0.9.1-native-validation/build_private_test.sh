#!/usr/bin/env bash
# Standalone opt-in validation client. Compiles ONLY against the already-built
# private libfprint tree and never installs any system libraries or touches USB.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
SRC="${FT5955_LIBFPRINT_SRC:-$HOME/Projects/libfprint-ft5955}"
BUILD="${FT5955_LIBFPRINT_BUILD:-$SRC/build-ft5955}"
[[ -f "$SRC/libfprint/fprint.h" ]] || { echo 'Missing private libfprint header' >&2; exit 2; }
[[ -f "$BUILD/libfprint/libfprint-2.so.2" ]] || { echo 'Missing built private libfprint library' >&2; exit 2; }
for dep in glib-2.0 gio-2.0 gobject-2.0; do
  pkg-config --exists "$dep" || { echo "Missing dependency: $dep" >&2; exit 2; }
done
mkdir -p build-tests
# Intentional shell splitting for pkg-config compiler/linker flags.
# shellcheck disable=SC2046
cc -std=gnu11 -Wall -Wextra -Werror -O2 \
  -I "$SRC/libfprint" -I "$BUILD/libfprint" \
  $(pkg-config --cflags glib-2.0 gio-2.0 gobject-2.0) \
  tests/native_print_roundtrip.c -L "$BUILD/libfprint" \
  -Wl,-rpath,"$BUILD/libfprint" -lfprint-2 \
  $(pkg-config --libs glib-2.0 gio-2.0 gobject-2.0) \
  -o build-tests/native_print_roundtrip
if ! ldd build-tests/native_print_roundtrip | grep -F "$BUILD/libfprint/libfprint-2.so.2"; then
  echo 'Safety stop: test is NOT linked to private libfprint.' >&2
  exit 3
fi
printf 'PASS: compiled against isolated libfprint; no USB, template or system changes.\n'
