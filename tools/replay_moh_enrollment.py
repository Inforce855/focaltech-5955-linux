#!/usr/bin/env python3
"""Offline 5955 enrolment diagnostic using existing private PGM captures.

Invokes the audited isolated batch runner. Displays only quality, coverage,
matching score, HRESULT and rejection diagnostics; never prints/saves pixels,
templates or the vendor DLL. No USB access or sudo required.
"""
import argparse
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
BATCH=ROOT/"tools/test_moh_isolated_pgm_enroll_batch.sh"

def matched(pattern, data, default="-"):
    m=re.search(pattern,data)
    return m.group(1) if m else default

def summarize(log, files):
    marks=list(re.finditer(r"\[5955\] Enrolment sample (\d+)/(\d+):", log))
    if not marks:
        print("No per-sample enrolment records found. Probe may have failed.",file=sys.stderr)
        return False
    print("\nSample  Quality  Area  Match score  Update HRESULT / reject   Status HRESULT / reject")
    print("-"*87)
    accepted=0
    rejected=0
    complete=False
    found_match=False
    inconsistent=[]
    extended=[]
    for n,m in enumerate(marks):
        end=marks[n+1].start() if n+1<len(marks) else len(log)
        section=log[m.start():end]
        index=int(m.group(1))
        if not 1<=index<=len(files):
            print("Invalid per-sample marker; stopping.",file=sys.stderr)
            return False
        quality=matched(r"focal_SendImageAndGetQualityAreaCond\.\.\.quality = (\d+)",section)
        area=matched(r"focal_SendImageAndGetQualityAreaCond\.\.\.quality = \d+, area = (\d+)",section)
        scores=re.findall(r"FtVerifyByTemplate\.\.\.leave, gVerifyScores = (\d+)",section)
        score=scores[-1] if scores else "-"
        if score not in ("-","0"):found_match=True
        update=re.search(r"ENROLL_DIAG update_hr=0x([0-9a-fA-F]{8}) update_reject=(\d+)",section)
        status=re.search(r"ENROLL_DIAG status_hr=0x([0-9a-fA-F]{8}) status_reject=(\d+)",section)
        up=(f"0x{update.group(1)} / {update.group(2)}" if update else "-")
        st=(f"0x{status.group(1)} / {status.group(2)}" if status else "-")
        if update and status and update.group(1).lower()=="00000000" and status.group(1).lower()=="00090001":
            inconsistent.append(index)
        ex_hr=matched(r"ENROLL_EXT call_hr=0x([0-9a-fA-F]{8})",section)
        ex_meta=re.search(r"ENROLL_EXT template_hr=0x([0-9a-fA-F]{8}) reject=(\d+) percent=(\d+) factor=(\d+) subfactor=(\d+)",section)
        ex_counts=re.search(r"ENROLL_EXT general=(\d+) center=(\d+) top=(\d+) bottom=(\d+) left=(\d+) right=(\d+)",section)
        if ex_hr!="-":
            extended.append((index,ex_hr,ex_meta,ex_counts))
        outcome=matched(r"\[5955\] UpdateEnrollment sample \d+: (-?\d+)",section)
        if outcome=="0":complete=True;accepted+=1
        elif outcome=="1":accepted+=1
        elif outcome=="2":rejected+=1
        print(f"{index:>4}    {quality:>4}   {area:>4}     {score:>5}       {up:<23} {st}")
    print("-"*87)
    print(f"Processed: {len(marks)}  |  Incomplete/needs more: {accepted - int(complete)}"
          f"  |  Rejected: {rejected}  |  Complete: {'YES' if complete else 'NO'}")
    if extended:
        print("\nExtended enrollment status (engine-reported; counters are requirements, not accepted touches):")
        print("Capture  Call HRESULT  Template HRESULT  Progress   General Center Top Bottom Left Right")
        for index,hr,meta,counts in extended:
            template=("0x"+meta.group(1)) if meta else "-"
            progress=(meta.group(3)+"%") if meta else "-"
            values=(" ".join(counts.groups()) if counts else "unavailable")
            print(f"{index:>6}   0x{hr}     {template:<13} {progress:>5}     {values}")
        if not any(meta is not None for _,_,meta,_ in extended):
            print("Extended status was not supplied; do not infer any area coverage.")
    if inconsistent:
        nums=", ".join(map(str,inconsistent))
        print(f"STATUS DISAGREEMENT at capture(s): {nums}")
        print("  UpdateEnrollment=S_OK (no more features required),")
        print("  but GetEnrollmentStatus=WINBIO_I_MORE_DATA (more data required).")
        print("  This is not confirmed enrolment completion. Audit the")
        print("  engine workflow, its setup calls and the WinBio pipeline.")
    print("A zero internal match score is not proof of a failed identity verification.")
    if found_match:print("At least one nonzero internal match score was observed.")
    else:print("No nonzero internal match score was observed in this run.")
    print("No biometric template was committed or saved.")
    return True

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive",type=Path,help="local FocalTech driver ZIP")
    ap.add_argument("--captures-dir",type=Path,
                    default=ROOT/"local-data/enroll-captures")
    ap.add_argument("--with-extended-status",action="store_true",
                    help="opt-in offline query of WinBio extended enrollment status (ABI experimental)")
    ap.add_argument("--with-enrollment-parameters",action="store_true",
                    help="opt-in offline call to standard WinBio SetEnrollmentParameters after CreateEnrollment")
    ap.add_argument("--limit",type=int,default=16,
                    help="number of existing PGM images, 2-20 (default: 16)")
    args=ap.parse_args()
    if not 2<=args.limit<=20:ap.error("--limit must be between 2 and 20")
    if not args.archive.is_file():ap.error("Driver archive not found")
    if not args.captures_dir.is_dir():ap.error("Private capture directory not found")
    files=sorted(args.captures_dir.glob("enroll_capture_*.pgm"))[:args.limit]
    if len(files)<2:ap.error("At least two existing PGM captures required")
    for path in files:
        st=path.lstat()
        if not stat.S_ISREG(st.st_mode):
            ap.error(f"Not a regular private PGM file: {path}")
    print(f"Replaying {len(files)} existing local PGM captures. No USB or new scans.")
    if args.with_enrollment_parameters:
        print("EXPERIMENT: SetEnrollmentParameters enabled (unknown finger subtype).")
    if args.with_extended_status:
        print("EXPERIMENT: QueryExtendedEnrollmentStatus enabled; isolated vendor DLL call.")
    try:
        proc=subprocess.run(
            ["bash",str(BATCH),*(["--with-enrollment-parameters"] if args.with_enrollment_parameters else []),*(["--with-extended-status"] if args.with_extended_status else []),str(args.archive.resolve()),*map(str,files)],
            cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,timeout=120,check=False)
    except subprocess.TimeoutExpired:
        print("Isolated diagnostic timed out.",file=sys.stderr)
        return 1
    if proc.returncode:
        print(f"Isolated diagnostic failed (exit {proc.returncode}).",file=sys.stderr)
        # Print only non-biometric setup diagnostics, never uncontrolled DLL logs.
        for name in ("create_hr","set_params_hr"):
            result=re.search(r"ENROLL_DIAG "+name+r"=0x([0-9a-fA-F]{8})",proc.stderr)
            if result:
                print(f"{name}=0x{result.group(1)}",file=sys.stderr)
        return proc.returncode
    setup=re.search(r"ENROLL_DIAG set_params_hr=0x([0-9a-fA-F]{8}) subfactor=(\d+)",proc.stderr)
    if args.with_enrollment_parameters:
        print("SetEnrollmentParameters result:",(f"0x{setup.group(1)}; subfactor={setup.group(2)}" if setup else "NOT CONFIRMED"))
    ok=summarize(proc.stderr,files)
    return 0 if ok else 1

if __name__=="__main__":
    raise SystemExit(main())
