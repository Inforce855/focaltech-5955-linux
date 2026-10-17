#!/usr/bin/env bash
# No sudo; real private libfprint library, purely synthetic template.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
SOURCE="${FT5955_LIBFPRINT_SRC:-$HOME/Projects/libfprint-ft5955}"
BUILD="${FT5955_LIBFPRINT_BUILD:-$SOURCE/build-ft5955}"
[[ -f "$SOURCE/libfprint/fp-print.h" && -f "$SOURCE/libfprint/fpi-print.h" ]] || {
    echo "Missing private libfprint headers: $SOURCE/libfprint" >&2
    exit 2
}
for dep in glib-2.0 gobject-2.0 gio-2.0 openssl; do
    pkg-config --exists "$dep" || { echo "Missing pkg-config development dependency: $dep" >&2; exit 2; }
done
mapfile -t LIBS < <(find -L "$BUILD/libfprint" -maxdepth 1 -type f -name 'libfprint-2.so*' | sort -V)
if (( ${#LIBS[@]} == 0 )); then
    echo "No private libfprint-2 shared object found in $BUILD/libfprint" >&2
    exit 2
fi
LIB=$(readlink -f "${LIBS[0]}")
mkdir -p ./build-test
FLAGS=$(pkg-config --cflags glib-2.0 gobject-2.0 gio-2.0 openssl)
# Word splitting intended for pkg-config flags.
# shellcheck disable=SC2086
cc -std=gnu11 -Wall -Wextra -Werror -O2 \
   -DFT5955_EXTERNAL_TEST \
   -I "$SOURCE/libfprint" -I ./driver -I "$BUILD/libfprint" $FLAGS \
   driver/ft5955_print_codec.c driver/ft5955_fpi_print_bridge.c tests/fpprint_roundtrip.c \
   "$LIB" $(pkg-config --libs glib-2.0 gobject-2.0 gio-2.0 openssl) \
   -Wl,-rpath,"$(dirname "$LIB")" \
   -o ./build-test/fpprint_roundtrip
G_DEBUG=fatal-warnings ./build-test/fpprint_roundtrip
