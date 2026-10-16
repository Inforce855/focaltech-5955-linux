#!/usr/bin/env bash
# Build one userspace test linked ONLY to the isolated libfprint checkout.
# No sudo, no system install, no biometric capture in the build phase.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
SRC="${FT5955_LIBFPRINT_SRC:-$HOME/Projects/libfprint-ft5955}"
BUILD="${FT5955_LIBFPRINT_BUILD:-$SRC/build-ft5955}"
[[ -f "$SRC/libfprint/fprint.h" ]] || { echo 'Private libfprint header missing' >&2; exit 2; }
[[ -d "$BUILD/libfprint" ]] || { echo 'Private libfprint build missing' >&2; exit 2; }
mkdir -p build-tests
# Intentional splitting of pkg-config compiler/link arguments.
# shellcheck disable=SC2046
cc -std=gnu11 -Wall -Wextra -Werror -O2 \
  -I "$SRC/libfprint" -I "$BUILD/libfprint" \
  $(pkg-config --cflags glib-2.0 gio-2.0 gobject-2.0) \
  tests/native_enroll_verify.c -L "$BUILD/libfprint" \
  -Wl,-rpath,"$BUILD/libfprint" -lfprint-2 \
  $(pkg-config --libs glib-2.0 gio-2.0 gobject-2.0) \
  -o build-tests/native_enroll_verify
printf '%s\n' 'PASS: private libfprint test client compiled. No USB accessed.'
printf 'For a deliberate live test later, configure the opt-in environment and run: %s\n' "$PWD/build-tests/native_enroll_verify --live"
