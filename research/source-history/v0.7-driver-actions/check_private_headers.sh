#!/usr/bin/env bash
# Compile-only private libfprint internal API check. No USB or sudo.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
SRC="${FT5955_LIBFPRINT_SRC:-$HOME/Projects/libfprint-ft5955}"
BUILD="${FT5955_LIBFPRINT_BUILD:-$SRC/build-ft5955}"
[[ -f "$SRC/libfprint/fpi-device.h" && -f "$SRC/libfprint/fprint.h" ]] || {
    echo "Private libfprint headers missing: $SRC/libfprint" >&2; exit 2;
}
mkdir -p build-test
FLAGS=$(pkg-config --cflags glib-2.0 gobject-2.0 gio-2.0 openssl)
# Intentional shell word splitting of pkg-config flag sequence.
# shellcheck disable=SC2086
cc -std=gnu11 -Wall -Wextra -Werror -O2 -c \
  -I "$SRC/libfprint" -I "$BUILD/libfprint" -I . $FLAGS \
  ft5955_fpi_action_bridge.c -o build-test/ft5955_fpi_action_bridge.o
printf '%s\n' 'PASS: FT5955 callback adapter compiles against private libfprint internals (no driver linked)'
