#!/usr/bin/env python3
"""Experimental 5955 MOH live test with versioned, private print envelope.

Does not save fingerprint images or templates. The envelope is kept in RAM,
not written to disk and not passed to fprintd. Real USB explicitly --live.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import struct
import subprocess
import sys

from print_codec import encode, decode, wipe, MAX_TEMPLATE

DEFAULT_MOH = Path.home() / 'Projects/focaltech-5955-moh-test'
DEFAULT_V04 = Path.home() / 'Projects/ft5955-moh-template-v0.4'


def live_main(moh_dir: Path, v04_dir: Path):
    if os.geteuid() == 0:
        raise RuntimeError('Run as ordinary user, not root')
    tools = moh_dir / 'tools'
    helper_file = tools / 'auto_contact_capture.py'
    runner = v04_dir / 'template_runner.py'
    for p in (helper_file, runner):
        if not p.is_file() or p.is_symlink():
            raise RuntimeError('Required trusted existing file unavailable: ' + str(p))
    if subprocess.run(['sudo','-n','true'], check=False,
                      stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        raise RuntimeError('Run sudo -v before enabling the existing bounded USB helper')
    sys.path.insert(0,str(tools))
    sys.path.insert(0,str(v04_dir))
    from live_finger_identify import prepared_pixels
    from template_restart_client import PrivateEngine
    from live_capture_client import capture_batch, prompt, MAX_BATCHES, MAX_FRAMES

    command=[sys.executable,str(runner)]
    helper=['sudo','-n',sys.executable,str(helper_file)]
    engine=PrivateEngine(command)
    envelope=None
    packet=None
    restored=None
    print('FT5955 MOH versioned-print boundary (experimental, RAM only).')
    print('One 12-impression enrolment, private print encode/decode, engine restart, verification.')
    print('No fprintd, libfprint or persistent template writes. q exits at a prompt.')
    try:
        engine.start()
        total=0; complete=False
        for batch in range(MAX_BATCHES):
            prompt(f'Enrol: Enter starts bounded batch {batch+1}; q quits: ')
            complete,count,rejected=capture_batch(engine,'SAMPLE',helper,prepared_pixels)
            total+=count
            if complete: break
            print(f'  Batch ended: {count} captured, {rejected} rejected.')
            if total>=MAX_FRAMES: break
        if not complete:
            raise RuntimeError('Enrolment did not complete within bounded safety budget')
        packet=engine.export_template()
        if len(packet)<6: raise RuntimeError('Unexpected vendor template packet')
        n=struct.unpack_from('<I',packet)[0]
        if not 1<=n<=MAX_TEMPLATE or n+5!=len(packet):
            raise RuntimeError('Invalid vendor template length')
        envelope=encode(memoryview(packet)[5:],packet[4])
        wipe(packet);packet=None
        engine.close()
        engine=PrivateEngine(command)
        engine.start()
        restored,subfactor=decode(envelope)
        packet=bytearray(struct.pack('<IB',len(restored),subfactor))
        packet.extend(restored)
        engine.import_template(packet)
        wipe(packet);packet=None
        wipe(restored);restored=None
        wipe(envelope);envelope=None
        print('Versioned print validated; imported to FRESH MOH sandbox. No data saved.')
        print('Test same enrolled finger, then different fingers for NO_MATCH.')
        while True:
            prompt('Verify: Enter starts one scan; q quits: ')
            complete,count,_=capture_batch(engine,'VERIFY',helper,prepared_pixels,first_only=True)
            if not count: print('  No new impression received.')
    except (KeyboardInterrupt,EOFError):
        print('Cancelled. Private print and MOH template discarded.')
        return 0
    finally:
        for value in (packet, restored, envelope):
            if value is not None: wipe(value)
        engine.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--live',action='store_true',help='explicit physical USB opt-in')
    p.add_argument('--moh-dir',type=Path,default=DEFAULT_MOH)
    p.add_argument('--v04-dir',type=Path,default=DEFAULT_V04)
    args=p.parse_args()
    if not args.live: p.error('Use --live explicitly for hardware access')
    try:
        return live_main(args.moh_dir.resolve(),args.v04_dir.resolve())
    except (ValueError,RuntimeError,OSError) as exc:
        print('STOPPED: '+str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
