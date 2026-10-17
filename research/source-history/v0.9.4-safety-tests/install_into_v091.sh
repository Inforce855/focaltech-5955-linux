#!/usr/bin/env bash
# Copy test-only v0.9.4 sources into existing validation folder; refuse overwrites.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${FT5955_VALIDATION_DIR:-$HOME/Projects/ft5955-native-validation-v0.9.1}"
[[ $(id -u) -ne 0 ]] || { echo 'STOP: run as ordinary user, not sudo.' >&2; exit 2; }
[[ -d "$TARGET/tests" ]] || { echo "STOP: no existing v0.9.1 tests in $TARGET" >&2; exit 2; }
for destination in \
  "$TARGET/tests/native_verify_safety_v094.c" \
  "$TARGET/tests/ft5955_quality_proxy_v094.py" \
  "$TARGET/tests/test_quality_proxy_v094.py" \
  "$TARGET/build_verify_safety_v094.sh"; do
  [[ ! -e "$destination" ]] || { echo "STOP: existing file, not overwriting: $destination" >&2; exit 2; }
done
install -m 0644 "$HERE/tests/native_verify_safety_v094.c" "$TARGET/tests/native_verify_safety_v094.c"
install -m 0644 "$HERE/tests/ft5955_quality_proxy_v094.py" "$TARGET/tests/ft5955_quality_proxy_v094.py"
install -m 0644 "$HERE/tests/test_quality_proxy_v094.py" "$TARGET/tests/test_quality_proxy_v094.py"
install -m 0644 "$HERE/tools/build_ft5955_verify_safety_v094.sh" "$TARGET/build_verify_safety_v094.sh"
cd "$TARGET"
bash -n build_verify_safety_v094.sh
python3 tests/test_quality_proxy_v094.py
bash build_verify_safety_v094.sh
