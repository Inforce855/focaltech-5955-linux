#!/usr/bin/env python3
"""Exact-source, reversible FT5955 native libfprint development patch.

Default --check is READ ONLY. --apply backs up exact original files and copies
only driver-specific sources into the chosen isolated development checkout.
Never installs, uses sudo, accesses USB, or modifies system authentication.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
FILES={
    'libfprint/drivers/focaltech_5955.c': None,
    'libfprint/meson.build': None,
}
# Validates against the two sources uploaded by the user.
EXPECTED={
    'libfprint/drivers/focaltech_5955.c':'d52470d1d4c9ba9f460dd03b3ac286f11f537b5515c2456db17899a5f4b010c1',
    'libfprint/meson.build':'f474a89dea3a9dcfb8f17424c857d13ddaadba064c8d93bf77075548f491b1c1',
}
SUPPORT=[p.name for p in (HERE/'driver').glob('*.c')]+[p.name for p in (HERE/'driver').glob('*.h')]

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def patch_driver(data:str)->str:
    marker='  dev_class->close = dev_close;'
    if data.count(marker)!=1 or data.count('#include "drivers_api.h"')!=1:
        raise RuntimeError('Driver differs from expected integration layout')
    data=data.replace('#include "drivers_api.h"',
                      '#include "drivers_api.h"\n#include "ft5955_native_action.h"',1)
    return data.replace(marker, marker+'\n  dev_class->enroll = ft5955_native_enroll;\n  dev_class->verify = ft5955_native_verify;',1)

def patch_meson(data:str)->str:
    marker="    'focaltech_5955' : files('drivers/focaltech_5955.c'),"
    if data.count(marker)!=1 or data.count('] + optional_deps')!=1:
        raise RuntimeError('Meson source/dependency layout differs')
    names=['focaltech_5955.c']+sorted(p.name for p in (HERE/'driver').glob('*.c'))
    replacement="    'focaltech_5955' : files(\n"+''.join(f"        'drivers/{p}',\n" for p in names)+"    ),"
    data=data.replace(marker,replacement,1)
    return data.replace('] + optional_deps',
        "] + optional_deps\n\n# The MOH host template codec uses OpenSSL SHA-256.\nif 'focaltech_5955' in drivers\n    deps += dependency('openssl')\nendif",1)

def run():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.home()/'Projects/libfprint-ft5955')
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--check',action='store_true')
    group.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    root=args.root.expanduser().resolve()
    if not (root/'.git').exists() or not (root/'libfprint/meson.build').exists():
        raise RuntimeError('Expected isolated libfprint git checkout not found')
    updates={}
    for path,want in EXPECTED.items():
        original=root/path
        if not original.is_file():raise RuntimeError(f'Missing {path}')
        raw=original.read_bytes()
        if sha(raw)!=want:
            raise RuntimeError(f'{path} changed since uploaded snapshot; REFUSING TO PATCH')
        content=raw.decode('utf-8')
        new=patch_driver(content) if path.endswith('focaltech_5955.c') else patch_meson(content)
        updates[path]=new.encode('utf-8')
    existing=[p.name for p in (HERE/'driver').iterdir() if p.is_file() and (root/'libfprint/drivers'/p.name).exists()]
    if existing:raise RuntimeError('Refusing to overwrite existing integration files: '+', '.join(existing))
    for path in updates:
        backup=root/(path+'.pre-ft5955-v0.8.bak')
        if backup.exists():raise RuntimeError('Backup already exists; refusing to overwrite '+str(backup))
    if not args.apply:
        print('PASS: two exact source hashes, patch anchors, and 0 conflicting files. No files modified.')
        return
    # Files are preflighted above before ANY filesystem modification.
    for path,content in updates.items():
        original=root/path
        shutil.copy2(original,root/(path+'.pre-ft5955-v0.8.bak'))
        original.write_bytes(content)
    for name in SUPPORT:
        shutil.copy2(HERE/'driver'/name,root/'libfprint/drivers'/name)
    print('APPLIED: only isolated checkout driver/Meson sources changed; originals backed up.')
    print('Use `ninja -C build-ft5955` from that checkout; do NOT install system libfprint.')

if __name__=='__main__':
    try:run()
    except (OSError,RuntimeError,UnicodeError) as e:
        sys.exit('STOP: '+str(e))
