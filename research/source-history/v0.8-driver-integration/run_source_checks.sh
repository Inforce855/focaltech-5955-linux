#!/usr/bin/env bash
# No USB / no engine / no libfprint installation. Tests the C action state
# machine and synthetic gateway, then syntax checks all Python source.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p build-tests
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -I driver \
  driver/ft5955_action_core.c tests/test_action_core.c -o build-tests/actions
build-tests/actions
python3 -m unittest discover -s tests -p 'test_gateway.py' -v
bash run_tests.sh
python3 -m py_compile apply.py restore.py engine/*.py
printf '%s\n' 'PASS: v0.8 offline control protocol and pure action state tests'
