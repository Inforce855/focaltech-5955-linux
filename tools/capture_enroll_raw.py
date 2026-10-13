#!/usr/bin/env python3
"""Capture up to eight separate presses privately from existing audited USB helper.

Real USB access is restricted to auto_contact_capture.py under sudo.
Writes raw captures locally mode 0600; no uploads, DLL, or templates.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import sys
from live_contact_viewer import read_record
from image_transfer import RAW_LENGTH

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--send",action="store_true",help="Authorise bounded fresh-touch capture")
    ap.add_argument("--output-dir",type=Path,default=Path("local-data/enroll-captures"))
    args=ap.parse_args()
    if not args.send:
        ap.error("Explicit --send is required to access reader")
    directory=args.output_dir.resolve()
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(directory,0o700)
    helper=Path(__file__).with_name("auto_contact_capture.py")
    print("Lift fully, then touch again. Up to eight fresh presses; 2-minute limit.",flush=True)
    print(f"Private raw captures: {directory}",flush=True)
    count=0
    with subprocess.Popen(
        ["sudo","-n",sys.executable,str(helper)],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        cwd=helper.parents[1]
    ) as proc:
        try:
            while True:
                record=read_record(proc.stdout)
                if record is None: break
                kind,payload=record
                if kind==b"F":
                    if len(payload)!=RAW_LENGTH: raise ValueError("Invalid capture frame length")
                    count+=1
                    name=directory/f"enroll_capture_{count:02d}.raw"
                    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                    with os.fdopen(fd,"wb") as fp: fp.write(payload)
                    print(f"Captured {count}/8 -> {name.name}",flush=True)
                else:
                    message=payload.decode("utf-8","replace")
                    print(f"Sensor: {message}",flush=True)
                    if kind in (b"E",b"D"): break
        finally:
            if proc.stdin and not proc.stdin.closed: proc.stdin.close()
        code=proc.wait(timeout=15)
        if code:
            print(f"USB helper exit status: {code}",file=sys.stderr)
            return code
    print(f"Saved {count} private raw capture(s). No Windows DLL executed.")
    print("These are 10240-byte raw files, not yet converted to enrolment PGM.")
    return 0 if count else 1
if __name__=="__main__":
    raise SystemExit(main())
