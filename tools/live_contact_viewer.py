#!/usr/bin/env python3
"""Local automatic-on-touch FocalTech 2808:5955 fingerprint preview.

Start as a normal desktop user with --send, after terminal sudo -v.
The window automatically watches for OFF (0x06) -> ON (0x05), capturing
once per fresh contact. Lift/re-touch to capture again. NO button press
needed between frames and NO image requests while the finger stays lifted.

The privileged USB helper is bounded to 8 images or 240 status queries,
checks status at most twice per second, and sends only audited 5955
0x34/0x82/0x80/0x81 requests. No 0x87 scan-mode write, reset, automatic
capture retries, firmware operation, system driver or PAM changes.
Fresh scanning event semantics are experimental, not a proven WinBio driver.

USB helper pipes raw buffers privately to this unprivileged GUI. Frames are
rendered in memory without creating PNG/raw files, network or uploads.
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

from image_transfer import RAW_LENGTH
from raw_to_png import decode_samples, greyscale_png, to_8bit, upscale_nn
from scan_preflight_capture import count_blank_rows

WIDTH, HEIGHT, ZOOM = 64, 80, 6
MAX_STATUS_BYTES = 600
HELPER_SCRIPT = Path(__file__).resolve().with_name("auto_contact_capture.py")


def frame_statistics(raw: bytes) -> dict[str, float | int]:
    """Local aggregate-only summary, not a biometric matching score."""
    if len(raw) != RAW_LENGTH:
        raise ValueError("Image must contain exactly 10,240 bytes")
    leading, total, trailing, zero_pct = count_blank_rows(raw)
    values = decode_samples(raw, "little")
    top = sum(v == 0 for v in values[:20 * WIDTH]) / (20 * WIDTH) * 100
    middle = sum(v == 0 for v in values[20 * WIDTH:60 * WIDTH]) / (40 * WIDTH) * 100
    bottom = sum(v == 0 for v in values[60 * WIDTH:]) / (20 * WIDTH) * 100
    return dict(zeros=zero_pct, leading=leading, all_rows=total,
                trailing=trailing, top=top, middle=middle, bottom=bottom)


def preview_pngs(raw: bytes) -> tuple[bytes, bytes]:
    """In-memory grayscale image and white-for-exact-zero diagnostic map."""
    samples = decode_samples(raw, "little")
    contrast = to_8bit(samples)
    zeros = bytes(255 if sample == 0 else 0 for sample in samples)

    def encode(values: bytes) -> bytes:
        return greyscale_png(upscale_nn(values, WIDTH, HEIGHT, ZOOM),
                             WIDTH * ZOOM, HEIGHT * ZOOM)

    return encode(contrast), encode(zeros)


def read_exact(stream, n: int) -> bytes:
    """A pipe read may return fewer than requested bytes."""
    out = bytearray()
    while len(out) < n:
        part = stream.read(n - len(out))
        if not part:
            raise EOFError("Truncated private helper stream")
        out.extend(part)
    return bytes(out)


def read_record(stream) -> tuple[bytes, bytes] | None:
    """Read one bounded binary record; no printing or persistence of images."""
    first = stream.read(1)
    if not first:
        return None
    if first not in (b"F", b"S", b"E", b"D"):
        raise ValueError("Unexpected capture-helper message type")
    length = int.from_bytes(read_exact(stream, 2), "big")
    if first == b"F":
        if length != RAW_LENGTH:
            raise ValueError("Unexpected helper frame length")
    elif length > MAX_STATUS_BYTES:
        raise ValueError("Oversize status message")
    return first, read_exact(stream, length)


class ContactViewer:
    """Tk GUI: start exactly one bounded scan automatically upon --send."""

    def __init__(self, root, *, enabled: bool, original: bytes | None = None):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.enabled = enabled
        self.proc: subprocess.Popen | None = None
        self.mailbox: queue.Queue = queue.Queue()
        self.stopping = threading.Event()
        self.running = False
        self.closed = False
        self.images = []
        self.last_raw: bytes | None = None
        self.frames = 0

        root.title("FocalTech 5955 — automatic finger-contact viewer")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.close)

        outer = ttk.Frame(root, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        ttk.Label(outer, text="Automatically captures when your finger returns",
                  font=("Sans", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(outer, text="Fingerprint image — enhanced for viewing").grid(
            row=1, column=0)
        ttk.Label(outer, text="Zero map — white=original zero; black=nonzero").grid(
            row=1, column=1)
        self.left = tk.Label(outer, relief="solid", bd=1)
        self.right = tk.Label(outer, relief="solid", bd=1)
        self.left.grid(row=2, column=0, padx=(0, 8), pady=(4, 8))
        self.right.grid(row=2, column=1, pady=(4, 8))

        self.readout = tk.StringVar(value="No fingerprint acquired yet.")
        ttk.Label(outer, textvariable=self.readout, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.message = tk.StringVar(value=(
            "Preparing automatic detection..." if enabled
            else "Offline inspection only; USB not accessed."))
        ttk.Label(outer, textvariable=self.message, wraplength=780,
                  justify="left").grid(row=4, column=0, columnspan=2, sticky="w")

        bar = ttk.Frame(outer)
        bar.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.stop_button = ttk.Button(bar, text="Stop scanning", command=self.stop)
        self.stop_button.pack(side="left", padx=(0, 8))
        self.restart_button = ttk.Button(
            bar, text="Restart bounded session", command=self.start)
        self.restart_button.pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Close", command=self.close).pack(side="left")

        ttk.Label(outer, text=(
            "Start with your finger OFF the sensor. Place it gently to capture, "
            "then LIFT it fully and TOUCH again for the next image — no mouse "
            "click needed. Up to 8 captures in 2 minutes; press Stop at any time. "
            "Status checked at most twice a second, so lift for at least "
            "half a second. Exact zeros are NOT proof of missing finger contact. "
            "No images saved, uploaded or logged."
        ), wraplength=780).grid(row=6, column=0, columnspan=2,
                                sticky="w", pady=(10, 0))

        if original is not None:
            self.show_frame(original, "Previously saved local file (offline)")
        self.update_buttons()
        self.root.after(90, self.drain)
        if enabled:
            self.root.after(150, self.start)

    def update_buttons(self):
        self.stop_button.configure(
            state="normal" if self.running else "disabled")
        self.restart_button.configure(
            state="normal" if self.enabled and not self.running else "disabled")

    def show_frame(self, raw: bytes, label: str):
        import tkinter as tk
        original_png, zeros_png = preview_pngs(raw)
        self.images = [
            tk.PhotoImage(data=base64.b64encode(original_png).decode("ascii"),
                          format="png"),
            tk.PhotoImage(data=base64.b64encode(zeros_png).decode("ascii"),
                          format="png"),
        ]
        self.left.configure(image=self.images[0])
        self.right.configure(image=self.images[1])
        self.last_raw = raw
        stats = frame_statistics(raw)
        self.readout.set(
            f"{label} | Original zeros {stats['zeros']:.1f}% | "
            f"fully blank rows {stats['all_rows']} "
            f"(leading {stats['leading']}, trailing {stats['trailing']})\n"
            f"Top 20 {stats['top']:.1f}% | Middle 40 {stats['middle']:.1f}% "
            f"| Bottom 20 {stats['bottom']:.1f}%"
        )

    def start(self):
        """One CLI --send or GUI restart authorises a bounded session."""
        if self.running or self.closed or not self.enabled:
            return
        self.running = True
        self.frames = 0
        self.stopping.clear()
        self.message.set("Starting USB detection. Lift your finger until OFF is seen.")
        self.update_buttons()
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        cmd = ["sudo", "-n", sys.executable, str(HELPER_SCRIPT)]
        try:
            if self.stopping.is_set():
                return
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=HELPER_SCRIPT.parents[1],
            )
            self.proc = proc
            if self.stopping.is_set():
                self.request_stop(proc)
            while True:
                item = read_record(proc.stdout)
                if item is None:
                    break
                self.mailbox.put(("record", *item))
                if item[0] in (b"E", b"D"):
                    break
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()  # pipe EOF also stops any waiting USB helper
            try:
                exit_code = proc.wait(timeout=13)
                if exit_code and not self.stopping.is_set():
                    err = proc.stderr.read(350).decode("utf-8", "replace")
                    if not err:
                        err = f"USB helper exited with status {exit_code}"
                    self.mailbox.put(("error", err))
            except subprocess.TimeoutExpired:
                self.mailbox.put(("error", "USB helper did not stop within 13 seconds."))
        except Exception as exc:
            self.mailbox.put(("error", f"Viewer stopped: {type(exc).__name__}: {exc}"))
        finally:
            self.proc = None
            self.mailbox.put(("done",))

    def drain(self):
        if self.closed:
            return
        while True:
            try:
                item = self.mailbox.get_nowait()
            except queue.Empty:
                break
            if item[0] == "record":
                _, kind, content = item
                if kind == b"F":
                    self.frames += 1
                    self.show_frame(content, f"Fresh contact {self.frames}/8")
                elif kind == b"S":
                    self.message.set(content.decode("utf-8", "replace"))
                elif kind == b"D":
                    self.message.set(content.decode("utf-8", "replace"))
                elif kind == b"E":
                    self.message.set("Acquisition stopped: " +
                                     content.decode("utf-8", "replace"))
            elif item[0] == "error":
                if "password" in item[1].lower() or "sudo" in item[1].lower():
                    self.message.set(
                        "sudo authorisation unavailable. Close the window, "
                        "run sudo -v in the terminal and reopen.")
                else:
                    self.message.set(item[1])
            elif item[0] == "done":
                self.running = False
                self.update_buttons()
        self.root.after(90, self.drain)

    @staticmethod
    def request_stop(proc):
        if proc is None or proc.stdin is None or proc.stdin.closed:
            return
        try:
            proc.stdin.write(b"q")
            proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass

    def stop(self):
        self.stopping.set()
        self.message.set("Stopping capture after any current USB transfer.")
        self.request_stop(self.proc)

    def close(self):
        self.closed = True
        self.stopping.set()
        self.request_stop(self.proc)
        self.root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true",
                        help="start one automatic bounded 5955 scan session")
    parser.add_argument("--file", type=Path,
                        help="open a previous private raw capture (offline)")
    args = parser.parse_args()
    if os.geteuid() == 0:
        print("Run graphical viewer WITHOUT sudo. Use sudo -v first.",
              file=sys.stderr)
        return 3
    if not args.send and args.file is None:
        print("Choose --send for automatic detection or --file for offline view.",
              file=sys.stderr)
        return 2

    initial = None
    if args.file is not None:
        if args.file.is_symlink() or args.file.suffix != ".raw":
            print("Expected a local regular .raw file (no symbolic link).",
                  file=sys.stderr)
            return 3
        initial = args.file.read_bytes()
        if len(initial) != RAW_LENGTH:
            print("File must be exactly 10,240 bytes.", file=sys.stderr)
            return 3

    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception as exc:
        print(f"Tk desktop unavailable: {exc}", file=sys.stderr)
        return 2
    ContactViewer(root, enabled=args.send, original=initial)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
