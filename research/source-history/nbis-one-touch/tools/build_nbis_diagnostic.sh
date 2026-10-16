#!/usr/bin/env bash
# Compile a standalone, unprivileged NBIS probe against isolated libfprint.
# Does NOT change system libraries, fprintd, PAM, USB rules or firmware.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${HOME}/Projects/libfprint-ft5955-src"
BUILD="${HOME}/Projects/libfprint-ft5955-build"
LIB="${BUILD}/libfprint/libfprint-2.so"
OUT="${ROOT}/native/build/ft5955_nbis_probe"
if [[ ! -f "${SOURCE}/libfprint/fpi-image.h" || ! -e "${LIB}" ]]; then
  echo "Isolated libfprint files not found. Build it first using tools/build_isolated_libfprint.sh" >&2
  exit 1
fi
mkdir -p "${ROOT}/native/build"
cc -std=c11 -O2 -Wall -Wextra -Werror \
  -I"${SOURCE}/libfprint" \
  $(pkg-config --cflags gio-2.0) \
  "${ROOT}/native/ft5955_nbis_probe.c" \
  "${LIB}" \
  $(pkg-config --libs gio-2.0) \
  -Wl,-rpath,"${BUILD}/libfprint" \
  -o "${OUT}"
chmod 700 "${OUT}"
echo "Ready: ${OUT}"
echo "No changes to system libfprint/fprintd/PAM."
