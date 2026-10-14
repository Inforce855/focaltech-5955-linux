#!/usr/bin/env python3
"""FT5955 v0.9.2: do not report intermediate quality retries twice to libfprint.
Only edits the private driver's ft5955_fpi_action_bridge.c. No USB or sudo.
"""
from pathlib import Path
import argparse
import shutil
import sys
import tempfile

FILE = Path('libfprint/drivers/ft5955_fpi_action_bridge.c')
OLD = '''      if (result == FT5955_DRIVER_RETRY)
        {
          fpi_device_verify_report (device, FPI_MATCH_ERROR, NULL,
                                     fpi_device_retry_new (FP_DEVICE_RETRY_GENERAL));
          return TRUE; /* Another fresh scan is needed. */
        }'''
NEW = '''      if (result == FT5955_DRIVER_RETRY)
        {
          /* Quality rejection is internal while this verify operation
           * continues acquiring fresh touches. libfprint permits only ONE
           * result report for the entire verification operation. */
          g_message ("FT5955 scan rejected; lift and reposition finger");
          return TRUE;
        }'''
BACKUP = '.before-v092.bak'


def patch(root, apply):
    path = root / FILE
    source = path.read_text()
    if source.count(NEW) == 1 and OLD not in source:
        return 'ALREADY PATCHED'
    if source.count(OLD) != 1 or NEW in source or (
        'result == FT5955_DRIVER_MATCHED || result == FT5955_DRIVER_NOT_MATCHED'
        not in source
    ):
        raise ValueError('Unexpected source: no files modified')
    if not apply:
        return 'PASS: exact original verified; no files modified'
    backup = path.with_name(path.name + BACKUP)
    if backup.exists():
        raise ValueError('Backup already exists; no files modified')
    shutil.copy2(path, backup)
    try:
        path.write_text(source.replace(OLD, NEW, 1))
    except BaseException:
        shutil.copy2(backup, path)
        raise
    return 'PATCHED one source file; backup: ' + str(backup)


def selftest():
    fixture = OLD + '\nif (result == FT5955_DRIVER_MATCHED || result == FT5955_DRIVER_NOT_MATCHED) {}\n'
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / FILE
        path.parent.mkdir(parents=True)
        path.write_text(fixture)
        assert 'no files modified' in patch(root, False)
        assert path.read_text() == fixture
        assert patch(root, True).startswith('PATCHED')
        assert OLD not in path.read_text() and NEW in path.read_text()
        assert patch(root, True) == 'ALREADY PATCHED'
        assert path.with_name(path.name + BACKUP).read_text() == fixture
        path.write_text(fixture.replace('return TRUE;', 'return FALSE;'))
        try:
            patch(root, True)
        except ValueError:
            pass
        else:
            raise AssertionError('Unexpected content was allowed')
    print('PASS: offline exact source, backup, retry fix, idempotence and refusal tests')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--self-test', action='store_true')
    parser.add_argument('--root', type=Path, default=Path.home() / 'Projects/libfprint-ft5955')
    args = parser.parse_args()
    if args.self_test:
        selftest()
    else:
        print(patch(args.root.expanduser().resolve(), args.apply))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, AssertionError) as error:
        sys.exit('STOP: ' + str(error))
