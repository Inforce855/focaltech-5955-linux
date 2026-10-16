#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
bash -n build_private_test.sh
python3 -m unittest discover -s tests -p 'test_static.py' -v
