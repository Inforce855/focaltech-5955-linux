#!/usr/bin/env python3
"""Local, bounded FocalTech 2808:5955 fingerprint contact viewer.

No network and NO disk writes of fingerprint images. Tk GUI is unprivileged.
Each operator-triggered snapshot launches one sudo -n USB helper; the helper
returns exactly 10240 raw image bytes via a private local stdout pipe. Eight
frames max per user-started *guided* session, one click per fresh touch;
requests spaced >=1s, with no background or indefinite polling.

Only the individually tested 0x34, 0x82, 0x80, 0x81 commands are sent,
once each per frame. NO 0x87, reset, USB configuration or kernel-driver change.
This is NOT Windows-equivalent scan initialization, and zeros are NOT proven
to correspond to missing finger contact. Images stay private, in RAM.
"""
from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from image_transfer import RAW_LENGTH
from raw_to_png import (
    decode_samples, greyscale_png, to_8bit, upscale_nn,
)
from scan_preflight_capture import checked_packets, count_blank_rows, decode_preflight_reply
from protocol_codec import ProtocolError

WIDTH, HEIGHT = 64, 80
ZOOM = 6
MAX_FRAMES = 8
MIN_REQUEST_INTERVAL_SECONDS = 1.0


def frame_statistics(raw: bytes) -> dict[str, float | int]:
    """Offline aggregate metadata; no image or identifying feature output."""
    if len(raw) != RAW_LENGTH:
        raise ValueError("Incomplete 10240-byte image")
    leading, total, trailing, zero_pct = count_blank_rows(raw)
    values = decode_samples(raw, "little")
    top = sum(v == 0 for v in values[:20 * WIDTH]) / (20 * WIDTH) * 100
    middle = sum(v == 0 for v in values[20 * WIDTH:60 * WIDTH]) / (40 * WIDTH) * 100
    bottom = sum(v == 0 for v in values[60 * WIDTH:]) / (20 * WIDTH) * 100
    return dict(zeros=zero_pct, leading=leading, all_rows=total,
                trailing=trailing, top=top, middle=middle, bottom=bottom)


def preview_pngs(raw: bytes) -> tuple[bytes, bytes]:
    """Return two *in-memory* PNGs: enhanced sensor image and exact-zero map.

    Zero map WHITE means original unsigned little-endian sample is exactly 0;
    dark means nonzero. The map is NOT a physically validated contact mask.
    """
    samples = decode_samples(raw, "little")
    contrast = to_8bit(samples)
    zeros = bytes(255 if sample == 0 else 0 for sample in samples)
    def encode(values: bytes) -> bytes:
        return greyscale_png(upscale_nn(values, WIDTH, HEIGHT, ZOOM),
                             WIDTH * ZOOM, HEIGHT * ZOOM)
    return encode(contrast), encode(zeros)


def read_one() -> bytes:
    """One verified-command preflight+capture; never log/print biometrics."""
    try:
        import usb.core
        import usb.util
        from firmware_probe import (
            VID, PID, INTERFACE, ENDPOINT_OUT, ENDPOINT_IN,
            SEND_TIMEOUT_MS, validate_device, receive_reply,
        )
        from image_transfer import receive_limited, extract_image
    except ImportError as exc:
        raise RuntimeError("Project .venv is missing PyUSB") from exc

    packets = checked_packets()
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise RuntimeError("2808:5955 is not attached")
    claimed = False
    try:
        validate_device(dev)
        usb.util.claim_interface(dev, INTERFACE)
        claimed = True

        def exchange(index: int, image: bool = False) -> bytes:
            packet = packets[index]
            sent = dev.write(ENDPOINT_OUT, packet, timeout=SEND_TIMEOUT_MS)
            if sent != len(packet):
                raise RuntimeError("Short USB write; stopping")
            if image:
                raw = receive_limited(
                    lambda n, t: dev.read(ENDPOINT_IN, n, timeout=t),
                    seconds=10.0,
                )
            else:
                raw = receive_reply(dev)
            if not raw:
                raise RuntimeError("No USB response; no retry")
            return raw

        decode_preflight_reply(exchange(0), "handshake")
        if decode_preflight_reply(exchange(1), "finger") != 0x05:
            raise RuntimeError("No finger detected (status 0x06); no image read")
        time.sleep(0.010)
        decode_preflight_reply(exchange(2), "ready")
        image = extract_image(exchange(3, image=True))
        if len(image.pixels) != RAW_LENGTH:
            raise RuntimeError("Unexpected image payload length")
        return image.pixels
    finally:
        if claimed:
            try:
                usb.util.release_interface(dev, INTERFACE)
            except usb.core.USBError:
                print("Warning: could not release interface", file=sys.stderr)
        usb.util.dispose_resources(dev)


def helper_main() -> int:
    """Privileged *one-frame* process. stdout is raw bytes, no status text."""
    if os.geteuid() != 0:
        print("Helper must run via sudo -n.", file=sys.stderr)
        return 3
    try:
        raw = read_one()
        if len(raw) != RAW_LENGTH:
            raise ValueError("Invalid image length")
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
        return 0
    except (Exception,) as exc:
        # Never print raw biometric bytes or packet contents.
        print(f"Capture stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4


def invoke_helper() -> bytes:
    """Use a privileged child, not a root graphical desktop process."""
    cmd = ["sudo", "-n", sys.executable, str(Path(__file__).resolve()), "--helper"]
    result = subprocess.run(cmd, capture_output=True, timeout=14,
                            check=False, cwd=Path(__file__).resolve().parents[1])
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        if "password" in message.lower() or "terminal is required" in message.lower():
            message = "sudo authorisation expired. Close viewer, run sudo -v, reopen."
        raise RuntimeError(message[:450] or f"USB helper returned {result.returncode}")
    if len(result.stdout) != RAW_LENGTH:
        raise RuntimeError(f"Wrong image length: {len(result.stdout)} bytes")
    return result.stdout


class ContactViewer:
    """Tk GUI. Only one verified capture per explicit click; no USB polling."""

    def __init__(self, root, *, enabled: bool, original: bytes | None = None):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.enabled = enabled
        self.mailbox: queue.Queue = queue.Queue()
        self.working = False
        self.closed = False
        self.stopping = False
        self.session_limit = 0     # 0 = standalone single capture; 8 = guided session
        self.session_taken = 0     # successful images only
        self.last_started = 0.0
        self.images = []
        self.last_raw: bytes | None = None

        root.title("FocalTech 5955 — local fingerprint contact viewer")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.close)

        outer = ttk.Frame(root, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        ttk.Label(outer, text="Original sensor image and zero-value regions",
                  font=("Sans", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(outer, text="Raw image — contrast for viewing").grid(
            row=1, column=0)
        ttk.Label(outer, text="Exact zeros — white = 0, black = nonzero").grid(
            row=1, column=1)
        self.left = tk.Label(outer, relief="solid", bd=1)
        self.right = tk.Label(outer, relief="solid", bd=1)
        self.left.grid(row=2, column=0, padx=(0, 8), pady=(4, 8))
        self.right.grid(row=2, column=1, pady=(4, 8))

        self.readout = tk.StringVar(value="No image yet.")
        ttk.Label(outer, textvariable=self.readout, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.message = tk.StringVar(value=(
            "A NEW image needs a lift-and-touch cycle; capture only when touching."
            if enabled else "Offline inspection — no USB access."))
        ttk.Label(outer, textvariable=self.message, wraplength=780,
                  justify="left").grid(row=4, column=0, columnspan=2, sticky="w")

        bar = ttk.Frame(outer)
        bar.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.once = ttk.Button(bar, text="Capture one frame",
                               command=self.single_capture)
        self.once.pack(side="left", padx=(0, 8))
        self.series = ttk.Button(bar, text="Start 8-touch session",
                                 command=self.begin_session)
        self.series.pack(side="left", padx=(0, 8))
        self.next_btn = ttk.Button(bar, text="Capture next",
                                   command=self.next_capture)
        self.next_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(bar, text="End session", command=self.stop)
        self.stop_btn.pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Close", command=self.close).pack(side="left")

        ttk.Label(outer, text=(
            "During an 8-touch session, LIFT your finger completely, "
            "RE-TOUCH the sensor, then click Capture next. The viewer does "
            "not query the reader while your finger is lifted. "
            "No images are saved/uploaded; USB commands are unchanged. "
            "Do not press the PC power button."
        ), wraplength=780).grid(row=6, column=0, columnspan=2,
                                sticky="w", pady=(10, 0))
        self.update_controls()
        if original is not None:
            self.show_frame(original, "Previously saved local file (offline)")
        self.root.after(90, self.drain)

    def update_controls(self):
        idle = self.enabled and not self.working and self.session_limit == 0
        self.once.configure(state="normal" if idle else "disabled")
        self.series.configure(state="normal" if idle else "disabled")
        next_ok = (self.enabled and not self.working
                   and self.session_limit == MAX_FRAMES and not self.stopping
                   and self.session_taken < MAX_FRAMES)
        self.next_btn.configure(state="normal" if next_ok else "disabled")
        self.stop_btn.configure(
            state="normal" if self.session_limit or self.working else "disabled")

    def show_frame(self, raw: bytes, description: str):
        import tkinter as tk
        original_png, zero_png = preview_pngs(raw)
        self.images = [
            tk.PhotoImage(data=base64.b64encode(original_png).decode("ascii"),
                          format="png"),
            tk.PhotoImage(data=base64.b64encode(zero_png).decode("ascii"),
                          format="png"),
        ]
        self.left.configure(image=self.images[0])
        self.right.configure(image=self.images[1])
        self.last_raw = raw
        stats = frame_statistics(raw)
        self.readout.set(
            f"{description} | Zeros: {stats['zeros']:.1f}% | "
            f"all-zero rows: {stats['all_rows']} "
            f"(leading: {stats['leading']}, trailing: {stats['trailing']})\n"
            f"Top 20: {stats['top']:.1f}% | "
            f"Middle 40: {stats['middle']:.1f}% | "
            f"Bottom 20: {stats['bottom']:.1f}%"
        )

    def request_frame(self):
        """Initiate exactly ONE capture from an explicit button click."""
        if self.working or self.stopping or not self.enabled:
            return False
        now = time.monotonic()
        if self.last_started and now - self.last_started < MIN_REQUEST_INTERVAL_SECONDS:
            self.message.set("Please wait at least one second between captures.")
            return False
        self.last_started = now
        self.working = True
        self.update_controls()
        self.message.set("Reading one image. Keep your finger gently touching the reader.")
        threading.Thread(target=self.worker_once, daemon=True).start()
        return True

    def single_capture(self):
        if self.session_limit:
            return
        self.request_frame()

    def begin_session(self):
        """Start a guided session, not an automatic eight-frame polling loop."""
        if self.session_limit or self.working or not self.enabled:
            return
        self.session_limit = MAX_FRAMES
        self.session_taken = 0
        self.stopping = False
        self.update_controls()
        self.request_frame()

    def next_capture(self):
        if (self.session_limit == MAX_FRAMES and not self.working
                and self.session_taken < MAX_FRAMES):
            self.request_frame()

    def worker_once(self):
        try:
            self.mailbox.put(("frame", invoke_helper()))
        except Exception as exc:
            self.mailbox.put(("error", str(exc)))
        finally:
            self.mailbox.put(("done",))

    def drain(self):
        """Tk widgets are updated only on the GUI thread."""
        if self.closed:
            return
        while True:
            try:
                event = self.mailbox.get_nowait()
            except queue.Empty:
                break
            if event[0] == "frame":
                if not self.stopping:
                    if self.session_limit:
                        self.session_taken += 1
                        number = self.session_taken
                        self.show_frame(event[1], f"Fresh touch {number}/{MAX_FRAMES}")
                        if number < MAX_FRAMES:
                            self.message.set(
                                f"{number}/{MAX_FRAMES} complete. Now LIFT your "
                                "finger, RE-TOUCH, then click Capture next. "
                                "No automatic scans will be sent.")
                        else:
                            self.message.set(
                                "All eight fresh touches captured. Session complete.")
                            self.session_limit = 0
                    else:
                        self.show_frame(event[1], "Single capture")
                        self.message.set(
                            "Snapshot complete. Lift and re-touch before another scan.")
            elif event[0] == "error":
                if self.stopping:
                    continue
                if self.session_limit and "No finger detected" in event[1]:
                    # User clicked while lifting; do not lose earlier captures.
                    # The next scan still requires a fresh physical click.
                    self.message.set(
                        f"{self.session_taken}/{MAX_FRAMES} complete. Finger "
                        "not present when checked. Re-touch, then click "
                        "Capture next; no automatic retry.")
                else:
                    self.message.set("Capture stopped: " + event[1])
                    self.session_limit = 0
            elif event[0] == "done":
                self.working = False
                if self.stopping:
                    self.session_limit = 0
                    self.message.set("Session ended. No further USB requests.")
                    self.stopping = False
                self.update_controls()
        self.root.after(90, self.drain)

    def stop(self):
        """Stop only future captures. Any current USB read finishes normally."""
        if self.session_limit or self.working:
            if self.working:
                self.stopping = True
                self.message.set("Stopping after the current one-shot USB request.")
            else:
                self.session_limit = 0
                self.session_taken = 0
                self.message.set("Session ended. No further USB requests.")
            self.update_controls()

    def close(self):
        self.stopping = True
        self.closed = True
        self.root.destroy()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true",
                        help="enable interactive user-triggered USB captures")
    parser.add_argument("--file", type=Path,
                        help="view one private 10240-byte .raw capture offline")
    parser.add_argument("--helper", action="store_true",
                        help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.helper:
        if args.send or args.file:
            print("Invalid helper options", file=sys.stderr)
            return 3
        return helper_main()
    if os.geteuid() == 0:
        print("Run the GUI WITHOUT sudo. First authorise USB with sudo -v.",
              file=sys.stderr)
        return 3
    if not args.send and args.file is None:
        print("Specify --file PATH for offline inspection or --send for live.",
              file=sys.stderr)
        return 2

    initial = None
    if args.file is not None:
        if args.file.is_symlink() or args.file.suffix != ".raw":
            print("Expected a normal, private .raw file (no symlink)", file=sys.stderr)
            return 3
        initial = args.file.read_bytes()
        if len(initial) != RAW_LENGTH:
            print("File is not 10240 bytes", file=sys.stderr)
            return 3

    try:
        import tkinter as tk
    except ImportError:
        print("Tkinter unavailable. Install Nobara's python3-tkinter package.",
              file=sys.stderr)
        return 2
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Could not open the desktop display: {exc}", file=sys.stderr)
        return 2
    ContactViewer(root, enabled=args.send, original=initial)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
