#!/usr/bin/env python3
"""Convert local 10240-byte 5955 captures to private 64x80 P5 PGM files.

Uses the existing little-endian percentile-contrast interpretation used by
the live viewer. This is an experimental calibration hypothesis, not an
assertion that the earlier Windows candidate used identical preprocessing.
No biometric bytes are printed or uploaded.
"""
import argparse
import os
from pathlib import Path
from raw_to_png import decode_samples, to_8bit, RAW_BYTES

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir",type=Path,default=Path("local-data/enroll-captures"))
    args=parser.parse_args()
    folder=args.input_dir.resolve()
    files=sorted(folder.glob("enroll_capture_*.raw"))
    if not files:
        parser.error(f"No enrolment .raw captures found in {folder}")
    converted=0
    skipped=0
    for source in files:
        target=source.with_suffix(".pgm")
        if target.exists():
            skipped+=1
            print(f"Already converted: {target.name} (kept unchanged)",flush=True)
            continue
        raw=source.read_bytes()
        if len(raw)!=RAW_BYTES:
            raise SystemExit(f"Wrong capture size: {source.name} ({len(raw)} bytes)")
        pixels=to_8bit(decode_samples(raw,"little"))
        if len(pixels)!=64*80:
            raise SystemExit("Unexpected image dimensions")
        payload=b"P5\n64 80\n255\n"+pixels
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as stream:stream.write(payload)
        converted+=1
        print(f"Private PGM ready: {target.name} (64x80)",flush=True)
    print(f"Converted {converted} new capture(s); skipped {skipped} existing PGM(s). RAW files retained. No biometric data uploaded.")
if __name__=="__main__":
    main()
