#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname "${BASH_SOURCE[0]}")"
python3 -m unittest discover -s tests -p 'test_print_codec.py' -v
python3 -m py_compile print_codec.py
printf '\nOffline codec tests completed. To test the ACTUAL private libfprint FpPrint\n'
printf 'serialisation on Nobara without USB or sudo, run: bash run_fpprint_test.sh\n'
