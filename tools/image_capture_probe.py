#!/usr/bin/env python3
"""Experimental single-shot or four-capture FocalTech 2808:5955 image reader.

The Windows MOH image helper at VA 0x18000793C sends command 0x81 and
expects 2 * width * height bytes. This probe deliberately DOES NOT issue
the unverified 0x87 scan-mode change; a scan may therefore yield no data.
Hardware image-read response format has not yet been confirmed.

Dry-run by default. --send opts into live USB, and each capture requires\npressing Enter after placing the finger. --session runs A1, A2, B1, B2.
Never share, publish or commit captured biometric samples.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import stat
import sys

from image_transfer import RAW_LENGTH, extract_image, receive_limited
from protocol_codec import ProtocolError, encode_command

COMMAND = 0x81
AUDITED_PACKET = bytes.fromhex('02 00 01 81 80')


def private_output_folder() -> Path:
    """Private local-data folder, owned by the original sudo invoker."""
    directory = Path.cwd() / 'local-data'
    if directory.is_symlink():
        raise OSError('local-data is a symbolic link: refusing biometric storage')
    uid = int(os.environ.get('SUDO_UID', os.getuid()))
    gid = int(os.environ.get('SUDO_GID', os.getgid()))
    directory.mkdir(mode=0o700, exist_ok=True)
    meta = directory.stat()
    if not stat.S_ISDIR(meta.st_mode):
        raise OSError('local-data is not a normal directory')
    if meta.st_uid not in (uid, 0):
        raise OSError('local-data is owned by an unexpected user')
    if meta.st_mode & 0o077:
        raise OSError('local-data permissions are not private (must be 0700)')
    if os.geteuid() == 0 and uid != 0 and meta.st_uid == 0:
        os.chown(directory, uid, gid)
    return directory


def save_private_raw(pixels: bytes, *, label: str | None = None) -> Path:
    """Never overwrite existing fingerprint captures or make public files."""
    if len(pixels) != RAW_LENGTH:
        raise ValueError('Image length disagrees with reported sensor dimensions')
    if label is not None and label not in ('A1', 'A2', 'B1', 'B2'):
        raise ValueError('Invalid capture label')
    directory = private_output_folder()
    suffix = '_' + label if label else ''
    name = 'fingerprint_' + datetime.now().strftime('%d-%m-%Y_%H-%M-%S') + suffix + '.raw'
    output = directory / name
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(output, flags, 0o600)
    try:
        uid = int(os.environ.get('SUDO_UID', os.getuid()))
        gid = int(os.environ.get('SUDO_GID', os.getgid()))
        if os.geteuid() == 0 and uid != 0:
            os.fchown(fd, uid, gid)
        with os.fdopen(fd, 'wb') as handle:
            fd = -1
            handle.write(pixels)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        output.unlink(missing_ok=True)
        raise
    return output


def live_capture(*, label: str | None = None) -> int:
    """One USB OUT request; bounded IN reception; no mode change."""
    try:
        import usb.core
        import usb.util
        from firmware_probe import (
            VID, PID, INTERFACE, ENDPOINT_OUT, ENDPOINT_IN,
            SEND_TIMEOUT_MS, SafetyAbort, validate_device, timed_out,
        )
    except ImportError:
        print('PyUSB is required for a live capture.', file=sys.stderr)
        return 2

    device = usb.core.find(idVendor=VID, idProduct=PID)
    if device is None:
        print('FocalTech 2808:5955 not found.', file=sys.stderr)
        return 1
    claimed = False
    try:
        validate_device(device)
        usb.util.claim_interface(device, INTERFACE)
        claimed = True
        print('Sending a single experimental 0x81 image-read request.')
        sent = device.write(ENDPOINT_OUT, AUDITED_PACKET, timeout=SEND_TIMEOUT_MS)
        print(f'USB OUT: {sent}/{len(AUDITED_PACKET)} bytes.')
        if sent != len(AUDITED_PACKET):
            print('Short write. No retry.', file=sys.stderr)
            return 4

        try:
            wire = receive_limited(
                lambda count, timeout: device.read(ENDPOINT_IN, count, timeout=timeout),
                seconds=15.0,
            )
        except usb.core.USBError as error:
            if timed_out(error):
                print('USB IN timed out. No image file was saved.')
                return 5
            raise
        except ProtocolError as error:
            print(f'Received invalid USB fragments: {error}. No file saved.')
            return 6

        print(f'USB IN: {len(wire)} bytes received (contents kept private).')
        try:
            image = extract_image(wire)
        except ProtocolError as error:
            print(f'Not a complete 80 x 64 sample buffer: {error}.')
            print('No file saved. Do not blindly retry or change scan mode.')
            return 6

        destination = save_private_raw(image.pixels, label=label)
        print('IMAGE BUFFER RECEIVED:', image.format)
        print('Saved privately:', destination)
        print('Raw sample byte order and pixel mapping remain unverified.')
        print('Convert without sudo:')
        print('  .venv/bin/python tools/raw_to_png.py',
              destination.relative_to(Path.cwd()))
        return 0
    except SafetyAbort as error:
        print(f'SAFETY STOP: {error}', file=sys.stderr)
        return 3
    except usb.core.USBError as error:
        print(f'USB error: {error}', file=sys.stderr)
        return 4
    except (OSError, ValueError) as error:
        print(f'Saving/validation error: {error}', file=sys.stderr)
        return 7
    except KeyboardInterrupt:
        print('\\nInterrupted. No more commands will be sent.')
        return 130
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, INTERFACE)
            except usb.core.USBError as error:
                print(f'Warning: failed to release interface: {error}',
                      file=sys.stderr)
        usb.util.dispose_resources(device)


CAPTURE_SEQUENCE = (
    ('A1', 'Finger A — first capture'),
    ('A2', 'Finger A — second capture'),
    ('B1', 'Finger B — first capture'),
    ('B2', 'Finger B — second capture'),
)


def wait_for_enter(message: str, *, input_fn=None) -> bool:
    """Capture only on an empty Enter. Any other input cancels safely."""
    if input_fn is None:
        input_fn = input
    try:
        answer = input_fn(message)
    except (KeyboardInterrupt, EOFError):
        print('\nCapture cancelled; no USB command sent for this step.')
        return False
    if answer:
        print('Cancelled (only an empty Enter triggers a capture).')
        return False
    return True


def run_session(*, capture_fn=None, input_fn=None) -> int:
    """Exactly four opt-in image reads; no polling and no automatic retries.

    One physical action (Enter) is required immediately before each command.
    No capture proceeds if the previous command fails.
    """
    if capture_fn is None:
        capture_fn = live_capture
    print('Four-capture session: A1, A2, B1, B2.')
    print('Place finger A twice, then switch to finger B for two captures.')
    print('Lift and reposition between captures; touch the power key LIGHTLY.')
    print('Each Enter sends ONE experimental image-read command 0x81.')
    print('Any other input or Ctrl+C stops; previously saved files stay private.')
    completed = 0
    for index, (label, description) in enumerate(CAPTURE_SEQUENCE, start=1):
        prompt = f'\n[{index}/4] {description}. Place finger, then press Enter (q + Enter cancels): '
        if not wait_for_enter(prompt, input_fn=input_fn):
            print(f'Session stopped. {completed} of 4 captures completed.')
            return 3
        try:
            status = capture_fn(label=label)
        except KeyboardInterrupt:
            print('\nInterrupted after capture request; no more commands will be sent.')
            return 130
        if status:
            print(f'Session stopped on {label} (status {status}). '
                  f'{completed} earlier capture(s) retained; no automatic retry.')
            return status
        completed += 1
        if completed < 4:
            print(f'Saved capture {label}. Lift/reposition your finger when ready.')
    print('\nAll four captures completed. Original samples remain in ignored local-data/.')
    print('Next (without sudo):')
    print('  .venv/bin/python tools/fingerprint_compare.py --latest-four')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send', action='store_true',
                        help='authorise live 0x81 image read(s); Enter before each')
    parser.add_argument('--session', action='store_true',
                        help='four separate Enter-triggered captures (A1, A2, B1, B2)')
    args = parser.parse_args()
    if encode_command(COMMAND) != AUDITED_PACKET:
        print('SAFETY STOP: packet differs from audited bytes.', file=sys.stderr)
        return 3
    print('FocalTech 2808:5955 — controlled fingerprint image capture')
    print('USB OUT per capture:', AUDITED_PACKET.hex(' '))
    print(f'Expected sample buffer: {RAW_LENGTH} bytes (80 x 64 x 2).')
    print('No explicit scan-mode change; no firmware/configuration writes.')
    print('Fingerprint image contents remain PRIVATE on this computer.')
    print('Mode:', 'four-capture session' if args.session else 'one-shot capture')
    if not args.send:
        print('DRY RUN: no USB access and no files created.')
        print('To proceed: sudo .venv/bin/python tools/image_capture_probe.py '
              + ('--session --send' if args.session else '--send'))
        return 0
    print('CAUTION: command 0x81 can initiate a sensor read or change temporary')
    print('device state. A physical Enter is required for each experimental read.')
    if args.session:
        return run_session()
    if not wait_for_enter(
        'Lightly touch the sensor, then press Enter to capture (q + Enter cancels): '
    ):
        return 3
    return live_capture()


if __name__ == '__main__':
    raise SystemExit(main())
