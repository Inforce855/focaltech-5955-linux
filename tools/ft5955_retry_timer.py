#!/usr/bin/env python3
"""FT5955 lab-only bounded verification retries and event timing.

Requires the already active experimental timing-trace fprintd service.
No enrolment, PAM changes, driver writes, or biometric data capture.
"""
import argparse
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

EVENT = re.compile(r"FT5955TIMING phase=([a-z_]+) mono_us=(\d+)")
VERDICT = re.compile(r"Verify result: (verify-[\w-]+)")

def delta(start, finish):
    if start is None or finish is None or finish < start:
        return "n/a"
    return f"{(finish-start)/1000:.1f} ms"

def follow_journal(events, halt):
    proc = None
    try:
        proc = subprocess.Popen(
            ["sudo", "-n", "journalctl", "--follow", "--lines=0",
             "--output=cat", "--unit=fprintd.service"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1)
        for line in proc.stdout:
            if halt.is_set():
                break
            match = EVENT.search(line)
            if match:
                events.put((match.group(1), int(match.group(2))))
    except OSError as error:
        events.put(("reader_error", str(error)))
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

def drain(events):
    trace = {}
    while True:
        try:
            key, value = events.get_nowait()
        except queue.Empty:
            break
        if key == "reader_error":
            print(f"Journal reader error: {value}", file=sys.stderr)
        else:
            trace[key] = value
    return trace

def verify(finger, timeout):
    started = time.monotonic()
    proc = subprocess.Popen(
        ["fprintd-verify", "-f", finger], stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1)
    output = []
    def collect():
        for line in proc.stdout:
            line = line.rstrip("\n")
            output.append(line)
            print(line, flush=True)
    reader = threading.Thread(target=collect, daemon=True)
    reader.start()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print("TIMEOUT: terminating current verification.")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    reader.join(timeout=2)
    verdict = next((m.group(1) for line in output
                    if (m := VERDICT.search(line))), None)
    return verdict, time.monotonic() - started

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finger", default="left-index-finger")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument("--no-journal", action="store_true")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your normal user, never root")
    if not 1 <= args.attempts <= 10 or not 5 <= args.timeout <= 120:
        parser.error("attempts must be 1–10 and timeout 5–120 seconds")
    if shutil.which("fprintd-verify") is None:
        parser.error("fprintd-verify is unavailable")
    if not args.no_journal and (shutil.which("sudo") is None or
                                shutil.which("journalctl") is None):
        parser.error("journalctl/sudo missing (or use --no-journal)")
    events = queue.Queue()
    halt = threading.Event()
    follower = None
    if not args.no_journal:
        subprocess.run(["sudo", "-v"], check=True)
        follower = threading.Thread(target=follow_journal,
                                    args=(events, halt), daemon=True)
        follower.start()
        time.sleep(0.5)
    print("\nFT5955 RETRY TIMER (lab only; Ctrl+C to cancel)")
    print("Use separate deliberate contacts; no automatic enrolment.\n")
    results = []
    previous_contact = None
    previous_verdict = None
    session_start = time.monotonic()
    try:
        for index in range(1, args.attempts + 1):
            drain(events)
            print(f"\n=== Verification {index}/{args.attempts} ===", flush=True)
            verdict, seconds = verify(args.finger, args.timeout)
            time.sleep(0.3)  # Allow the journald reader to receive late events.
            trace = drain(events)
            contact = trace.get("contact_on_observed")
            reply = trace.get("matcher_reply_received")
            print(f"Result: {verdict or 'no terminal verdict'} | CLI: {seconds:.3f} s")
            if trace:
                print("Gateway startup:          ",
                      delta(trace.get("worker_start"), trace.get("gateway_ready")))
                print("Contact → image:          ",
                      delta(contact, trace.get("image_captured")))
                print("Image → matcher reply:    ",
                      delta(trace.get("image_captured"), reply))
                print("Matcher → verify finished:",
                      delta(reply, trace.get("verify_finish_done")))
                if previous_contact is not None:
                    print("Previous contact → next:  ", delta(previous_contact, contact))
                if previous_verdict is not None:
                    print("Previous verdict → contact:", delta(previous_verdict, contact))
            else:
                print("No trace events collected for this verification.")
            results.append((verdict, seconds))
            if contact is not None:
                previous_contact = contact
            if reply is not None:
                previous_verdict = reply
            if verdict == "verify-match":
                break
            if index != args.attempts:
                print("No match. Lift and reposition for another try.")
                time.sleep(0.65)
    except KeyboardInterrupt:
        print("\nCancelled; no configuration changed.")
    finally:
        halt.set()
        if follower:
            follower.join(timeout=2)
    matched = sum(v == "verify-match" for v, _ in results)
    rejected = sum(v == "verify-no-match" for v, _ in results)
    print(f"\nSUMMARY: {len(results)} verifications, {matched} match, "
          f"{rejected} no-match; {time.monotonic()-session_start:.3f} s elapsed")
    print("Inter-contact timing includes press duration and retry startup.")
    print("Exact release-to-next-contact awaits separate driver instrumentation.")
    return 0 if matched else 1

if __name__ == "__main__":
    sys.exit(main())
