#!/usr/bin/env python3
"""Hash-verified import of historical FT5955 text source into a separate Git branch.

Dry-run by default. --stage copies sources, --publish additionally commits and
pushes ONLY the research/source-history directory from the dedicated source-
history branch. No installers or archive scripts are run. This does not modify
libfprint, fprintd, PAM, USB permissions, or the user's active driver tree.
"""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

BRANCH = 'feature/ft5955-source-history'
DEST = Path('research/source-history')
KNOWN = {
    'd3030d7ba0d26a3f167ffbfbdf4067eaf199905f7ee75de31a4e0674d6f55231': 'v0.8-driver-integration',
    '0a9d00af12acd8899b84e1ce94af80e619f413a802cc01003c8ed8a038334a01': 'v0.1-moh-ipc',
    '4b8e91a4627a08631868520e915213d59836969472b755a8598cb5034b877db5': 'v0.2-moh-ipc',
    '50a0c23feda590abfce4e3457414b0121e36dec47f07b5147362fee8eab20c03': 'v0.3-moh-ipc',
    '6d284f8a762779b8bab11aa1b8f6548c51797005edd7c4d9bd57cc3063a8c892': 'v0.4-moh-template',
    '2a42fe076138ae923a7bf1ba29df7e3588ed72c9cffbeb76aaddf6224e39eb1f': 'v0.5-moh-print',
    '1c88fcf6f34ef13c795f00bf4525a09aae2556e832e449564cbcb8c4e4886ca1': 'v0.6-moh-libfprint',
    '53dd2b3d81da20c766993422c8829e2e673942c69f1722b434526357951c3726': 'v0.6.1-moh-libfprint',
    '039100b697dd6e059211cd522254a6edb45f176aa5425d9b47031edada31edad': 'v0.7-driver-actions',
    'cb56078de9d0dcbe67a4cfbc529fdaa98810d0f8410c8344464f8e6b34ea7d2f': 'driver-sources-snapshot',
    'b734dc99f60b1cbae18956d5138a392fe674fada5eab944fedc48374aa209e63': 'v0.9-native-validation',
    '857d445ee7dc01e11a1aa7cec3bb9cdeb4685e859e0f2784631110877fb1979f': 'v0.9.1-native-validation',
    '3762811926d28afd035241c649c27222d8ab7745f1591c4b8a84878243049a8d': 'v0.9.4-safety-tests',
    '5457c2c1d7cc1262c9c5749dfd9364a5da461bc7ad02dfac973aa60176a6b465': 'v0.9.6-private-enroll-initial',
    'f349b6c311bc4f6b69173a1a98b39b114e1c54c9afa3b8fbbb37830343f14c3e': 'live-libfprint-original',
    '13d0ed22fc07116bad31b6375605f67ceb67fe6caf145370d0be88a34ba1bf5b': 'live-libfprint-2x-scale',
    '0aeef7ab90fc57e0582cdc47b02a2381c75393892ac978ef091e128bc5d3a450': 'nbis-one-touch',
}
ALLOWED = {'.c', '.h', '.py', '.sh', '.md', '.txt', '.diff', '.build'}


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def sources_from(inputs):
    found = set()
    for arg in inputs:
        path = Path(arg).expanduser()
        if path.is_dir():
            found.update(path.glob('*.tar.gz'))
            # Re-downloaded archives often have '(1)' before the .gz extension.
            found.update(path.glob('*.tar(*).gz'))
        elif path.is_file():
            found.add(path)
        else:
            raise ValueError(f'Missing path: {path}')
    return sorted(found)


def inspect(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest not in KNOWN:
        return None
    tag = KNOWN[digest]
    result, skipped, total = [], 0, 0
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive.getmembers():
            name = member.name
            parts = PurePosixPath(name).parts
            if (not name or name.startswith('/') or '\\' in name or
                    not parts or any(part in ('..', '.', '') for part in parts)):
                raise ValueError(f'Unsafe tar path: {name}')
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f'Unsupported tar member type: {name}')
            if '__pycache__' in parts or name.endswith('.pyc'):
                skipped += 1
                continue
            if member.size > 1_048_576:
                raise ValueError(f'Unexpectedly large source: {name}')
            if parts[0].startswith('ft5955-') and len(parts) > 1:
                parts = parts[1:]
            if not parts or PurePosixPath(*parts).suffix not in ALLOWED:
                raise ValueError(f'Unexpected file type: {name}')
            data = archive.extractfile(member).read()
            if len(data) != member.size:
                raise ValueError(f'Truncated tar member: {name}')
            text = data.decode('utf-8')
            if '\x00' in text or '-----BEGIN PRIVATE KEY-----' in text:
                raise ValueError(f'Unexpected content in: {name}')
            total += len(data)
            if total > 5_000_000:
                raise ValueError(f'Archive exceeds uncompressed limit: {path}')
            result.append((DEST / tag / Path(*parts), data))
    return tag, result, skipped


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('sources', nargs='+', help='Directories containing archives or tar.gz paths')
    p.add_argument('--repo', default='~/Projects/focaltech-5955-linux')
    p.add_argument('--stage', action='store_true', help='Copy historic text source into a clean source-history worktree')
    p.add_argument('--publish', action='store_true', help='Stage, commit and push to the source-history branch')
    args = p.parse_args()
    root = Path(args.repo).expanduser().resolve()
    writing = args.stage or args.publish
    if writing:
        if git(root, 'rev-parse', '--show-toplevel') != str(root):
            raise SystemExit('Refusing a nested or unexpected Git repository path')
        if git(root, 'branch', '--show-current') != BRANCH:
            raise SystemExit(f'Use a clean checkout of {BRANCH}, not your active working branch')
        if git(root, 'status', '--porcelain'):
            raise SystemExit('The source-history checkout has local changes; no files touched')
        if args.publish:
            if git(root, 'rev-parse', 'HEAD') != git(root, 'rev-parse', f'origin/{BRANCH}'):
                raise SystemExit('Local and remote history branch differ; fetch/review before importing')

    planned, count, omitted = {}, 0, 0
    archives = sources_from(args.sources)
    for archive in archives:
        entry = inspect(archive)
        if entry is None:
            omitted += 1
            continue
        tag, files, skipped = entry
        count += 1
        print(f'{tag}: {len(files)} UTF-8 source files, {skipped} cached binaries skipped')
        for target, data in files:
            if target in planned and planned[target] != data:
                raise SystemExit(f'Archive content collision: {target}')
            planned[target] = data
    if not planned:
        raise SystemExit('No recognised archives found; nothing changed')
    for relative, data in planned.items():
        target = root / relative
        if any((root.joinpath(*relative.parts[:i])).is_symlink()
               for i in range(1, len(relative.parts) + 1)):
            raise SystemExit(f'Symlink in target path: {target}')
        if target.exists() and target.read_bytes() != data:
            raise SystemExit(f'Existing file differs; no files overwritten: {target}')
    print(f'{count}/{len(archives)} archives recognised; {omitted} other archives ignored.')
    print(f'{len(planned)} versioned source files validated. Mode: ' +
          ('publish' if args.publish else 'stage' if args.stage else 'DRY RUN'))
    if not writing:
        print('Nothing changed. Use --stage or --publish only from a clean source-history branch.')
        return
    for relative, data in planned.items():
        target = root / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    if args.publish:
        git(root, 'add', '--', str(DEST))
        changed = git(root, 'diff', '--cached', '--name-only')
        if not changed:
            print('Nothing new to commit; historical source already present.')
            return
        if any(not name.startswith(f'{DEST}/') for name in changed.splitlines()):
            raise SystemExit('Unexpected staged file: no commit or push')
        print(f'Commit: {len(changed.splitlines())} newly staged historical source files')
        git(root, 'commit', '-m', f'Import {count} historical FT5955 source archives (source only)')
        git(root, 'push', 'origin', BRANCH)
        print('PUSHED:', git(root, 'rev-parse', '--short', 'HEAD'))
    else:
        print('Staged to research/source-history; no commit/push performed.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        raise SystemExit(f'IMPORT STOPPED: {exc}') from exc
