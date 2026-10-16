#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p build-test
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -I driver \
  driver/ft5955_action_core.c tests/test_action_core.c -o build-test/test_action_core
./build-test/test_action_core
