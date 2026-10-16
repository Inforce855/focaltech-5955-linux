#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m py_compile template_runner.py template_restart_client.py live_capture_client.py
