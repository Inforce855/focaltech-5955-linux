#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
bash native/run_tests.sh
python3 test_adapter.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
