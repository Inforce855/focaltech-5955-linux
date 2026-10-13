#!/usr/bin/env bash
# Build only: no proprietary DLL execution or USB access.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p native/build
gcc -std=gnu11 -O0 -g -Wall -Wextra -Wno-unused-parameter \
  -pthread -Iengine engine/ft_engine.c engine/ft5955_compat_time.c \
  engine/ft5955_compat_fls.c engine/ft5955_compat_locale.c \
  engine/ft5955_compat_datetime.c \
  tools/moh_engine_interface_smoke.c \
  -lm -o native/build/ft5955_moh_smoke
printf 'Built native/build/ft5955_moh_smoke (not executed).\n'
