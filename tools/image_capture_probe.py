#!/usr/bin/env python3
"""Experimental one-shot FocalTech 2808:5955 fingerprint image read.

The Windows MOH image helper at VA 0x18000793C sends command 0x81 and
expects 2 * width * height bytes. This probe deliberately DOES NOT issue
the unverified 0x87 scan-mode change; a scan may therefore yield no data.
Hardware image-read response format has not yet been confirmed.

Dry-run by default. --send and manually entering CAPTURE are both required.
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


def save_private_raw(pixels: bytes) -> Path:
    """Never overwrite existing fingerprint captures or make public files."""
    if len(pixels) != RAW_LENGTH:
        raise ValueError('Image length disagrees with reported sensor dimensions')
    directory = private_output_folder()
    name = 'fingerprint_' + datetime.now().strftime('%d-%m-%Y_%H-%M-%S') + '.raw'
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


def live_capture() -> int:
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

        destination = save_private_raw(image.pixels)
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send', action='store_true',
                        help='one live 0x81 image request (requires CAPTURE)')
    args = parser.parse_args()
    if encode_command(COMMAND) != AUDITED_PACKET:
        print('SAFETY STOP: packet differs from audited bytes.', file=sys.stderr)
        return 3
    print('FocalTech 2808:5955 — one-shot experimental image read')
    print('USB OUT:', AUDITED_PACKET.hex(' '))
    print(f'Expected sample buffer: {RAW_LENGTH} bytes (80 x 64 x 2).')
    print('No explicit scan-mode change; no firmware/configuration writes.')
    print('No fingerprint image bytes will be printed or uploaded.')
    if not args.send:
        print('DRY RUN: no USB access and no files created.')
        return 0

    print('CAUTION: Unlike earlier metadata queries, command 0x81 may')
    print('trigger an image acquisition or affect temporary sensor state.')
    print('Its actual response on this 2808:5955 hardware is not yet known.')
    try:
        confirmation = input('Lightly touch the reader and type CAPTURE once: ')
    except (EOFError, KeyboardInterrupt):
        print('\\nCancelled.')
        return 3
    if confirmation != 'CAPTURE':
        print('Cancelled.')
        return 3
    return live_capture()


if __name__ == '__main__':
    raise SystemExit(main())
