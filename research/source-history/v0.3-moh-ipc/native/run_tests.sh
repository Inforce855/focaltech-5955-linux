#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cc -std=c11 -O2 -Wall -Wextra -Werror \
   -I native native/ft5955_ipc.c native/test_ft5955_ipc.c \
   -o native/test_ft5955_ipc
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
printf '#!/usr/bin/env bash\nexec "%s" "%s/fake_vendor_runner.py"\n' \
  "$(command -v python3)" "$PWD" > "$scratch/fake.sh"
chmod 700 "$scratch/fake.sh"
native/test_ft5955_ipc "$(command -v python3)" \
    "$PWD/moh_adapter.py" "$scratch/fake.sh"
