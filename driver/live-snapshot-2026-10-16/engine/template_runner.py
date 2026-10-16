#!/usr/bin/env python3
"""Use the existing audited vendor runner with one substituted C probe.

Only a temporary PRIVATE COPY of the shell script is modified. The user's
feature branch, DLL and working GUI remain unchanged. Exact-match checks
refuse unexpected upstream edits rather than bypassing safety checks.
"""
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
DEFAULT_MOH = Path.home() / 'Projects/focaltech-5955-moh-test'


def run(moh_dir=DEFAULT_MOH, executable=None):
    original = moh_dir / 'tools/test_moh_isolated_live_identify.sh'
    probe = HERE / 'template_session.c'
    if (not original.is_file() or original.is_symlink()
            or not probe.is_file() or probe.is_symlink()):
        raise RuntimeError('Missing original trusted runner or local C probe')
    source = original.read_text(encoding='utf-8')
    # Leave every SHA check, bubblewrap mount, namespace and compile flag intact.
    cd_line = 'cd "$(dirname "$0")/.."'
    c_file = 'tools/moh_engine_live_identify.c'
    if source.count(cd_line) != 1 or source.count(c_file) != 1:
        raise RuntimeError('Unexpected upstream runner; refusing to patch it')
    source = source.replace(cd_line, 'cd ' + shlex.quote(str(moh_dir.resolve())))
    source = source.replace(c_file, shlex.quote(str(probe)))
    # The original runner remains in place, unmodified.
    with tempfile.TemporaryDirectory(prefix='ft5955-template-runner-') as directory:
        private_copy = Path(directory) / 'runner.sh'
        private_copy.write_text(source, encoding='utf-8')
        private_copy.chmod(0o700)
        command = ['bash', str(private_copy)]
        if executable is not None:
            command.append(str(executable))
        return subprocess.call(command)


if __name__ == '__main__':
    if os.geteuid() == 0:
        sys.exit('Run as normal user, not root')
    try:
        sys.exit(run(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_MOH))
    except (OSError, RuntimeError) as exc:
        print(f'Template runner stopped: {exc}', file=sys.stderr)
        sys.exit(1)
