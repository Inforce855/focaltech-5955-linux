#!/usr/bin/env python3
"""Safely stage known historical FT5955 source archives without running them.

Read-only by default. --stage copies only UTF-8 source into an isolated
research/source-history tree in a clean GitHub development checkout.
It NEVER writes to libfprint, installed services, or system authentication.
"""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

BRANCH = 'feature/ft5955-private-fprintd-v096'
KNOWN = {
    'd3030d7ba0d26a3f167ffbfbdf4067eaf199905f7ee75de31a4e0674d6f55231': 'v0.8-driver-integration',
    '0a9d00af12acd8899b84e1ce94af80e619f413a802cc01003c8ed8a038334a01': 'v0.1-moh-ipc',
    '4b8e91a4627a08631868520e915213d59836969472b755a8598cb5034b877db5': 'v0.2-moh-ipc',
    'b734dc99f60b1cbae18956d5138a392fe674fada5eab944fedc48374aa209e63': 'v0.9-native-validation',
    '857d445ee7dc01e11a1aa7cec3bb9cdeb4685e859e0f2784631110877fb1979f': 'v0.9.1-native-validation',
    '3762811926d28afd035241c649c27222d8ab7745f1591c4b8a84878243049a8d': 'v0.9.4-safety-tests',
    'f349b6c311bc4f6b69173a1a98b39b114e1c54c9afa3b8fbbb37830343f14c3e': 'live-libfprint-original',
    '13d0ed22fc07116bad31b6375605f67ceb67fe6caf145370d0be88a34ba1bf5b': 'live-libfprint-2x-scale',
    '0aeef7ab90fc57e0582cdc47b02a2381c75393892ac978ef091e128bc5d3a450': 'nbis-one-touch',
    '5457c2c1d7cc1262c9c5749dfd9364a5da461bc7ad02dfac973aa60176a6b465': 'v0.9.6-private-enroll-initial',
}
ALLOWED = {'.c', '.h', '.py', '.sh', '.md', '.txt', '.diff'}
DEST = Path('research/source-history')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def paths_from_input(inputs):
    found = set()
    for arg in inputs:
        path = Path(arg).expanduser()
        if path.is_dir():
            found.update(path.glob('*.gz'))
        elif path.is_file():
            found.add(path)
        else:
            raise ValueError(f'Missing directory/archive: {path}')
    return sorted(found)


def read_archive(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest not in KNOWN:
        return None
    tag = KNOWN[digest]
    files = []
    with tarfile.open(path, 'r:gz') as archive:
        for m in archive.getmembers():
            p = PurePosixPath(m.name)
            if p.is_absolute() or any(x in ('', '.', '..') for x in p.parts):
                raise ValueError(f'Unsafe archive path: {m.name}')
            if m.isdir():
                continue
            if not m.isfile():
                raise ValueError(f'Unsafe tar member type: {m.name}')
            parts = p.parts
            if len(parts) > 1 and parts[0].startswith('ft5955-'):
                parts = parts[1:]
            relative = PurePosixPath(*parts)
            if relative.suffix not in ALLOWED or m.size > 1024 * 1024:
                raise ValueError(f'Unexpected file extension/size: {m.name}')
            data = archive.extractfile(m).read()
            data.decode('utf-8')  # refuse binary or damaged archives
            files.append((DEST / tag / Path(*relative.parts), data))
    return tag, files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('sources', nargs='+', help='Download folder(s) or individual .tar.gz paths')
    p.add_argument('--repo', default='~/Projects/focaltech-5955-linux')
    p.add_argument('--stage', action='store_true', help='Copy reviewed historical text sources; no commit/push')
    a = p.parse_args()
    root = Path(a.repo).expanduser().resolve()
    if a.stage:
        if git(root, 'branch', '--show-current') != BRANCH:
            raise SystemExit(f'--stage requires checkout of {BRANCH}')
        if git(root, 'status', '--porcelain'):
            raise SystemExit('Checkout is not clean; refusing to stage into an existing worktree')
    planned = {}
    for archive in paths_from_input(a.sources):
        entry = read_archive(archive)
        if entry is None:
            continue
        tag, files = entry
        print(f'{tag}: {len(files)} text files ({archive.name})')
        for relative, data in files:
            if relative in planned and planned[relative] != data:
                raise SystemExit(f'Conflicting target: {relative}')
            planned[relative] = data
    if not planned:
        raise SystemExit('No hash-recognised source archives found; nothing changed')
    for relative, data in planned.items():
        target = root / relative
        if target.is_symlink():
            raise SystemExit(f'Refusing symlink target: {target}')
        if target.exists() and target.read_bytes() != data:
            raise SystemExit(f'Existing source differs; refusing overwrite: {target}')
    print(f'{len(planned)} historical text files validated; mode={"stage" if a.stage else "DRY RUN"}.')
    if a.stage:
        for relative, data in planned.items():
            target = root / relative
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        print('Sources copied to research/source-history; review, git add, commit and push manually.')
    else:
        print('Nothing written. Pass --stage after inspecting your clean feature-branch checkout.')


if __name__ == '__main__':
    main()
