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
    infrastructure_error = any("NoSuchDevice" in line or "No devices available" in line or "Impossible to verify:" in line for line in output)
    return verdict, time.monotonic() - started, infrastructure_error

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finger", default="left-index-finger")
    parser.add_argument("--rounds", type=int, default=5,
                        help="Independent tests to run, even after a match")
    parser.add_argument("--retries", type=int, default=3,
                        help="Maximum verification operations per round")
    parser.add_argument("--attempts", type=int, default=None,
                        help="Deprecated alias for --retries")
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument("--no-journal", action="store_true")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your normal user, never root")
    if args.attempts is not None:
        args.retries = args.attempts
    if not 1 <= args.rounds <= 30 or not 1 <= args.retries <= 10 or not 5 <= args.timeout <= 120:
        parser.error("rounds 1–30, retries 1–10, timeout 5–120 seconds")
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
    rounds = []
    previous_contact = None
    previous_verdict = None
    session_start = time.monotonic()
    aborted = False
    try:
        for round_num in range(1, args.rounds + 1):
            print(f"\n######## ROUND {round_num}/{args.rounds} ########", flush=True)
            round_start = time.monotonic()
            outcomes = []
            for attempt in range(1, args.retries + 1):
                drain(events)
                print(f"\n--- Fingerprint attempt {attempt}/{args.retries} ---", flush=True)
                verdict, seconds, infrastructure_error = verify(args.finger, args.timeout)
                if infrastructure_error:
                    print("STOP: fingerprint service/device unavailable; no further retries.")
                    aborted = True
                    break
                time.sleep(0.3)
                trace = drain(events)
                contact = trace.get("contact_on_observed")
                reply = trace.get("matcher_reply_received")
                print(f"Result: {verdict or 'no terminal verdict'} | CLI: {seconds:.3f} s")
                if trace:
                    print("Gateway startup:            ",
                          delta(trace.get("worker_start"), trace.get("gateway_ready")))
                    print("Contact → image:            ",
                          delta(contact, trace.get("image_captured")))
                    print("Image → matcher reply:      ",
                          delta(trace.get("image_captured"), reply))
                    print("Matcher → verify finished:  ",
                          delta(reply, trace.get("verify_finish_done")))
                    if previous_contact is not None:
                        print("Previous contact → contact: ", delta(previous_contact, contact))
                    if previous_verdict is not None:
                        print("Previous verdict → contact: ", delta(previous_verdict, contact))
                else:
                    print("No timing trace events captured for this verification.")
                outcomes.append((verdict, seconds))
                if contact is not None:
                    previous_contact = contact
                if reply is not None:
                    previous_verdict = reply
                if verdict == "verify-match":
                    break
                if verdict != "verify-no-match":
                    print("STOP: no valid terminal verdict; no further retries.")
                    aborted = True
                    break
                if attempt < args.retries:
                    print("NO_MATCH: lift and reposition for the next attempt.")
                    time.sleep(0.65)
            if outcomes:
                successful = outcomes[-1][0] == "verify-match"
                duration = time.monotonic() - round_start
                rounds.append((successful, outcomes, duration))
                print(f"\nROUND {round_num}: {'MATCH' if successful else 'NO MATCH'} "
                      f"after {len(outcomes)} verification(s), {duration:.3f} s")
            if aborted:
                break
            if round_num < args.rounds:
                print("Next independent round: lift your finger until prompted.")
                time.sleep(0.8)
    except KeyboardInterrupt:
        print("\nCancelled; no configuration changed.")
        aborted = True
    finally:
        halt.set()
        if follower:
            follower.join(timeout=2)
    successes = sum(ok for ok, _, _ in rounds)
    total_attempts = sum(len(attempts) for _, attempts, _ in rounds)
    no_matches = sum(v == "verify-no-match" for _, attempts, _ in rounds
                     for v, _ in attempts)
    print(f"\nSUMMARY: {len(rounds)}/{args.rounds} rounds completed, "
          f"{successes} successful; {total_attempts} verifications, "
          f"{no_matches} no-match; {time.monotonic()-session_start:.3f} s elapsed")
    if rounds:
        print(f"First-attempt successes: {sum(ok and len(a) == 1 for ok,a,_ in rounds)}")
        print(f"Average round duration: {sum(d for _,_,d in rounds)/len(rounds):.3f} s")
    print("Inter-contact intervals include finger contact, human positioning, and new verification startup.")
    print("Exact release-to-next-contact awaits separate driver instrumentation.")
    return 0 if successes == len(rounds) == args.rounds and not aborted else 1

if __name__ == "__main__":
    sys.exit(main())
