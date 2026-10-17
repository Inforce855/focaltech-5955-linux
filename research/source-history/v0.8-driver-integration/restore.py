#!/usr/bin/env python3
"""Restore the exact two backed-up FT5955 files in the isolated worktree.

Does not delete other developer modifications. Safe fail if no backup present.
Manual verification of Git status is recommended before applying.
"""
from pathlib import Path
import argparse, shutil, sys
p=argparse.ArgumentParser()
p.add_argument('--root',type=Path,default=Path.home()/'Projects/libfprint-ft5955')
p.add_argument('--restore',action='store_true')
a=p.parse_args()
r=a.root.expanduser().resolve()
backups=[]
for f in ('libfprint/drivers/focaltech_5955.c','libfprint/meson.build'):
    original=r/f;backup=r/(f+'.pre-ft5955-v0.8.bak')
    if not backup.is_file() or not original.is_file():sys.exit('STOP: missing source/backup: '+f)
    backups.append((original,backup))
if not a.restore:
    print('Backups exist. To restore: python3 restore.py --restore');sys.exit(0)
for original,backup in backups:shutil.copy2(backup,original)
print('Restored original driver and Meson. New integration support files remain in worktree; remove them only after reviewing git status.')
