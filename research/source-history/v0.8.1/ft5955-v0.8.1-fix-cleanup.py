#!/usr/bin/env python3
"""Fix invalid GSubprocess pre-wait status probes in private FT5955 v0.8.

Edits ONLY native experimental integration source. Refuses unknown versions.
No USB, privileges, source downloads or system changes.
"""
from pathlib import Path
import sys

src = Path.home() / 'Projects/libfprint-ft5955/libfprint/drivers/ft5955_native_action.c'
if len(sys.argv) > 2:
    raise SystemExit('Usage: python3 ft5955-v0.8.1-fix-cleanup.py [path-to-private-source]')
if len(sys.argv) == 2:
    src = Path(sys.argv[1]).expanduser().resolve()
if not src.is_file() or src.is_symlink():
    raise SystemExit(f'Unexpected or missing source: {src}')
old = 'g_subprocess_get_if_exited(child)'
new = '(g_subprocess_get_identifier(child) == NULL)'
s = src.read_text()
if old not in s and s.count(new) == 5:
    print('ALREADY FIXED: five cleanup checks use safe process-liveness API.')
    raise SystemExit(0)
if s.count(old) != 5 or new in s or 'g_subprocess_wait(child,NULL,NULL)' not in s:
    raise SystemExit('UNEXPECTED SOURCE VERSION: no changes made.')
backup = src.with_suffix('.c.v08-pre-cleanup')
if backup.exists():
    raise SystemExit(f'Backup already exists; refusing to overwrite: {backup}')
backup.write_text(s)
src.write_text(s.replace(old, new))
assert src.read_text().count(new) == 5
print(f'PATCHED: five invalid pre-wait checks in {src}')
print(f'BACKUP: {backup}')
print('Next: ninja -C ~/Projects/libfprint-ft5955/build-ft5955')
