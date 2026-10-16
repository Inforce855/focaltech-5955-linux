#!/usr/bin/env python3
"""Live FocalTech 2808:5955 -> isolated libfprint virtual-image socket.

Only real fresh-contact USB captures from our audited auto_contact_capture.py
are accepted. No stored raws, images, biometric templates, network transport,
firmware changes, or system authentication changes. Run unprivileged; sudo is
used only by the existing tightly bounded USB helper.

The virtual-image protocol is two native gint32 (width, height) followed by
width * height grayscale bytes. The virtual driver reports finger on/off
around every incoming image. No fake fingerprint images are generated here.

The CLI defaults to a 2x enlargement for libfprint/NBIS rather than the
previous 10x enlargement borrowed from a SIFT-based driver. Both image scale
and interpolation are experimental and do not establish authentication quality.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import time

from raw_to_png import decode_samples, to_8bit

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "tools/auto_contact_capture.py"
DEFAULT_SOCKET = ROOT / "local-data/libfprint-live/fingerprint.sock"
NATIVE_CLI = ROOT / "native/build/ft5955_normalize_cli"
RAW_BYTES = 10_240
WIDTH, HEIGHT = 64, 80
# Preserve the original Python helper defaults for existing regression tests.
# The LIVE CLI explicitly defaults to scale=2 (NBIS experiment).
SCALE = 10
FRAME_BYTES = WIDTH * HEIGHT * SCALE * SCALE
ALLOWED_SCALES = (1, 2, 3, 4, 5, 10)
MAX_MESSAGE = 600


def read_exact(stream, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            raise EOFError("USB helper ended mid-record")
        data.extend(chunk)
    return bytes(data)


def read_record(stream) -> tuple[bytes, bytes] | None:
    kind = stream.read(1)
    if not kind:
        return None
    if kind not in (b"F", b"S", b"D", b"E"):
        raise ValueError("Unexpected private USB-helper record type")
    size = int.from_bytes(read_exact(stream, 2), "big")
    if kind == b"F":
        if size != RAW_BYTES:
            raise ValueError("Unexpected fingerprint frame size")
    elif size > MAX_MESSAGE:
        raise ValueError("Unexpected USB-helper status message size")
    return kind, read_exact(stream, size)


def normalize(raw: bytes, method: str) -> bytes:
    if len(raw) != RAW_BYTES:
        raise ValueError("Expected exactly 10,240 raw fingerprint bytes")
    if method == "native-v3":
        if NATIVE_CLI.is_symlink() or not NATIVE_CLI.is_file():
            raise RuntimeError(
                "Native converter not built: make -C native build/ft5955_normalize_cli"
            )
        result = subprocess.run(
            [str(NATIVE_CLI)], input=raw, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=15,
        )
        if result.returncode:
            raise RuntimeError(
                "Native v3 rejected an image: "
                + result.stderr.decode("utf-8", "replace").strip()[:200]
            )
        pixels = result.stdout
    elif method == "contrast":
        pixels = to_8bit(decode_samples(raw, "little"))
    else:
        raise ValueError("Unknown image conversion mode")
    if len(pixels) != WIDTH * HEIGHT:
        raise ValueError("Converter returned incorrect image dimensions")
    return pixels


def enlarge(pixels: bytes, scale: int = SCALE,
            interpolation: str = "cubic") -> bytes:
    """Scale the 64x80 8-bit image; do not invent extra fingerprint detail."""
    if len(pixels) != WIDTH * HEIGHT:
        raise ValueError("Invalid original greyscale image")
    if scale not in ALLOWED_SCALES:
        raise ValueError("Unsupported enlargement factor")
    if interpolation not in ("linear", "cubic"):
        raise ValueError("Unsupported interpolation method")
    if scale == 1:
        return pixels
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("OpenCV / NumPy missing from project venv") from exc
    source = np.frombuffer(pixels, dtype=np.uint8).reshape(HEIGHT, WIDTH)
    mode = cv2.INTER_LINEAR if interpolation == "linear" else cv2.INTER_CUBIC
    enlarged = cv2.resize(source, (WIDTH * scale, HEIGHT * scale),
                          interpolation=mode)
    result = enlarged.tobytes(order="C")
    if len(result) != WIDTH * HEIGHT * scale * scale:
        raise ValueError("Incorrect enlarged image size")
    return result


def send_image(sock: socket.socket, pixels: bytes, scale: int = SCALE) -> None:
    if scale not in ALLOWED_SCALES:
        raise ValueError("Unsupported enlargement factor")
    if len(pixels) != WIDTH * HEIGHT * scale * scale:
        raise ValueError("Incorrect greyscale image length for chosen scale")
    # C gint is 32-bit native endian; '=ii' uses native endian, fixed 4-byte ints.
    sock.sendall(struct.pack("=ii", WIDTH * scale, HEIGHT * scale) + pixels)


def connect_virtual(path: Path, wait_seconds: int) -> socket.socket:
    if path.is_symlink():
        raise ValueError("Refusing symlink at libfprint socket path")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("Start the isolated libfprint enrolment program first")
    mode = parent.stat()
    if mode.st_uid != os.getuid() or mode.st_mode & 0o077:
        raise ValueError("Socket parent must be owned by you and mode 0700")
    deadline = time.monotonic() + wait_seconds
    while True:
        if path.is_symlink():
            raise ValueError("Refusing symlink at libfprint socket path")
        if path.exists():
            if not stat.S_ISSOCK(path.stat().st_mode):
                raise ValueError("Expected a Unix socket, not a regular file")
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(str(path))
                return sock
            except (ConnectionRefusedError, FileNotFoundError):
                sock.close()
        if time.monotonic() >= deadline:
            raise TimeoutError("No libfprint virtual-image listener appeared")
        time.sleep(0.2)


def stop_helper(proc: subprocess.Popen) -> None:
    if proc.poll() is None and proc.stdin and not proc.stdin.closed:
        try:
            proc.stdin.write(b"q")
            proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
    if proc.stdin and not proc.stdin.closed:
        proc.stdin.close()
    try:
        proc.wait(timeout=13)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def live_bridge(path: Path, method: str, wait_seconds: int,
                scale: int = 2, interpolation: str = "linear") -> int:
    if os.geteuid() == 0:
        raise RuntimeError("Run as your normal user, NEVER with sudo")
    if scale not in ALLOWED_SCALES:
        raise ValueError("Unsupported enlargement factor")
    if interpolation not in ("linear", "cubic"):
        raise ValueError("Unsupported interpolation method")
    # Fail before USB access if OpenCV / converter isn't available.
    if method == "native-v3" and not NATIVE_CLI.is_file():
        raise RuntimeError("Build native converter first: make -C native build/ft5955_normalize_cli")
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Install opencv-python-headless in this project's .venv") from exc
    print("Connecting to isolated libfprint virtual-image listener...", flush=True)
    with connect_virtual(path, wait_seconds) as sock:
        sock.settimeout(15)
        # No stdin input: the helper is cancelled explicitly when the
        # virtual device closes, or after its eight-contact safety budget.
        command = ["sudo", "-n", sys.executable, str(HELPER)]
        proc = subprocess.Popen(command, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=ROOT)
        count = 0
        try:
            print("Live bridge connected. Lift your finger, then touch gently.", flush=True)
            print(f"Each fresh contact sends ONE real {WIDTH * scale} x {HEIGHT * scale} image to libfprint.", flush=True)
            print(f"Mode: {method}; scale={scale}x; interpolation={interpolation}.", flush=True)
            while True:
                record = read_record(proc.stdout)
                if record is None:
                    break
                kind, data = record
                if kind == b"S":
                    print("Sensor: " + data.decode("utf-8", "replace"), flush=True)
                elif kind == b"F":
                    image = enlarge(normalize(data, method), scale, interpolation)
                    try:
                        send_image(sock, image, scale)
                    except (BrokenPipeError, ConnectionResetError, socket.timeout) as exc:
                        print("libfprint closed its socket: " + str(exc), flush=True)
                        break
                    count += 1
                    print(f"Sent real impression {count}/8 ({WIDTH * scale} x {HEIGHT * scale} greyscale).", flush=True)
                elif kind == b"E":
                    raise RuntimeError("USB helper: " + data.decode("utf-8", "replace"))
                elif kind == b"D":
                    print("Sensor session: " + data.decode("utf-8", "replace"), flush=True)
                    break
            if proc.poll() not in (None, 0) and count == 0:
                message = proc.stderr.read(350).decode("utf-8", "replace").strip()
                if message:
                    print("USB helper: " + message, file=sys.stderr)
            print(f"Bridge finished; {count} real impressions transmitted.", flush=True)
            return 0 if count else 1
        finally:
            stop_helper(proc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET,
                        help="local virtual-image socket from isolated enroll")
    parser.add_argument("--processing", choices=("native-v3", "contrast"),
                        default="native-v3", help="real-scan normalisation method")
    parser.add_argument("--scale", type=int, choices=ALLOWED_SCALES, default=2,
                        help="image enlargement factor (default 2x for NBIS test)")
    parser.add_argument("--interpolation", choices=("linear", "cubic"),
                        default="linear", help="resize filter (default linear)")
    parser.add_argument("--wait", type=int, default=60,
                        help="seconds to wait for libfprint's socket (1..120)")
    args = parser.parse_args()
    if not 1 <= args.wait <= 120:
        parser.error("--wait must be 1..120 seconds")
    try:
        return live_bridge(args.socket, args.processing, args.wait,
                           args.scale, args.interpolation)
    except (OSError, RuntimeError, ValueError, TimeoutError, EOFError,
            subprocess.TimeoutExpired) as exc:
        print(f"Live bridge stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
