#!/usr/bin/env bash
# Standalone v0.9.3 probe: build against user's PRIVATE libfprint only.
# No sudo, installation, USB access, or scripts downloaded at build time.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

SRC="${FT5955_LIBFPRINT_SRC:-$HOME/Projects/libfprint-ft5955}"
BUILD="${FT5955_LIBFPRINT_BUILD:-$SRC/build-ft5955}"
TEST=tests/cancel_probe_v093.c
OUT=build-tests/cancel_probe_v093

[[ $(id -u) -ne 0 ]] || { echo "STOP: do not build/run as root." >&2; exit 2; }
[[ -f "$TEST" ]] || { echo "STOP: missing $TEST" >&2; exit 2; }
[[ -f "$SRC/libfprint/fprint.h" ]] || { echo "STOP: missing private libfprint header" >&2; exit 2; }
[[ -f "$BUILD/libfprint/libfprint-2.so.2" ]] || { echo "STOP: missing private libfprint shared library" >&2; exit 2; }
for dep in glib-2.0 gio-2.0 gobject-2.0; do
  pkg-config --exists "$dep" || { echo "STOP: missing $dep" >&2; exit 2; }
done

mkdir -p build-tests
# Intentional pkg-config flag splitting; validated as compiler flags.
# shellcheck disable=SC2046
cc -std=gnu11 -Wall -Wextra -Werror -O2 \
  -I "$SRC/libfprint" -I "$BUILD/libfprint" \
  $(pkg-config --cflags glib-2.0 gio-2.0 gobject-2.0) \
  "$TEST" -L "$BUILD/libfprint" -Wl,-rpath,"$BUILD/libfprint" \
  -lfprint-2 $(pkg-config --libs glib-2.0 gio-2.0 gobject-2.0) \
  -o "$OUT"
if ! ldd "$OUT" | grep -F "$BUILD/libfprint/libfprint-2.so.2"; then
  echo "STOP: private libfprint linkage could not be confirmed." >&2
  rm -f "$OUT"
  exit 3
fi
echo "PASS: cancellation diagnostic compiled against private libfprint."
echo "Run after setting opt-in environment:"
echo "  ./build-tests/cancel_probe_v093 --live-no-touch"
echo "  ./build-tests/cancel_probe_v093 --live-after-one"
