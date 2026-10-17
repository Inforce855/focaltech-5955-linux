#!/usr/bin/env bash
# Build a private libfprint with ONLY virtual_image. Never install over Nobara.
set -euo pipefail
src="$HOME/Projects/libfprint-ft5955-src"
bld="$HOME/Projects/libfprint-ft5955-build"
for tool in git meson ninja cc pkg-config; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
if [[ ! -d "$src" ]]; then
  git clone --depth 1 --branch v1.94.10 \
    https://gitlab.freedesktop.org/libfprint/libfprint.git "$src"
elif [[ ! -d "$src/.git" ]]; then
  echo "Source directory exists but is not a git checkout: $src" >&2; exit 2
fi
if [[ ! -f "$bld/build.ninja" ]]; then
  meson setup "$bld" "$src" \
    -Ddrivers=virtual_image \
    -Dintrospection=false -Dgtk-examples=false -Ddoc=false \
    -Dudev_rules=disabled -Dudev_hwdb=disabled
fi
meson compile -C "$bld"
echo "Isolated libfprint build ready: $bld"
echo "This script did NOT install, overwrite or configure system libfprint/fprintd."
