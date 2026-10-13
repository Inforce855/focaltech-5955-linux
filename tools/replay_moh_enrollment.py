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

def summarize(log, files, completion_from_update=False, probe_commit=False, skip_status=False, with_duplicate_check=False):
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
        st=(f"0x{status.group(1)} / {status.group(2)}" if status else ("not queried" if skip_status else "-"))
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
    if completion_from_update:
        print(f"Processed: {len(marks)}  |  Valid updates: {accepted}"
              f"  |  Rejected: {rejected}  |  UpdateEnrollment=S_OK reached: {'YES' if complete else 'NO'}")
        print("Windows-capture-workflow interpretation ONLY; GetEnrollmentStatus remains independent.")
        if probe_commit:
            print("Mock-storage CommitEnrollment probe requested. Identity verification is NOT TESTED.")
        else:
            print("Actual template commit and successful verification: NOT TESTED.")
    else:
        print(f"Processed: {len(marks)}  |  Incomplete/needs more: {accepted - int(complete)}"
              f"  |  Rejected: {rejected}  |  Complete by GetEnrollmentStatus: {'YES' if complete else 'NO'}")
    if extended:
        print("\nExtended enrollment status (raw engine fields; zeroes may indicate unsupported reporting):")
        print("Capture  Call HRESULT  Template HRESULT  Progress   General Center Top Bottom Left Right")
        for index,hr,meta,counts in extended:
            template=("0x"+meta.group(1)) if meta else "-"
            progress=(meta.group(3)+"%") if meta else "-"
            values=(" ".join(counts.groups()) if counts else "unavailable")
            print(f"{index:>6}   0x{hr}     {template:<13} {progress:>5}     {values}")
        if not any(meta is not None for _,_,meta,_ in extended):
            print("Extended status was not supplied; do not infer any area coverage.")
        elif all(meta is not None and meta.group(3)=="0" and counts is not None
                 and all(v=="0" for v in counts.groups()) for _,_,meta,counts in extended):
            print("WARNING: Percentage and regional fields are ALL ZERO throughout.")
            print("These do not establish 0% actual progress or zero required samples.")
            print("Treat extended coverage/progress as UNAVAILABLE until validated.")
    if inconsistent:
        nums=", ".join(map(str,inconsistent))
        print(f"STATUS DISAGREEMENT at capture(s): {nums}")
        print("  UpdateEnrollment=S_OK (no more features required),")
        print("  but GetEnrollmentStatus=WINBIO_I_MORE_DATA (more data required).")
        print("  The callbacks disagree. No template was committed or verified.")
        print("  Check the Windows capture workflow and engine lifecycle.")
    print("A zero internal match score is not proof of a failed identity verification.")
    if found_match:print("At least one nonzero internal match score was observed.")
    else:print("No nonzero internal match score was observed in this run.")
    if probe_commit:
        if with_duplicate_check:
            duplicate=re.search(r"DUPLICATE_PROBE hr=0x([0-9a-fA-F]{8}) duplicate=(\d+)",log)
            if duplicate:
                print("DUPLICATE PRECHECK:",f"HRESULT=0x{duplicate.group(1)};",
                      f"duplicate found={'YES' if duplicate.group(2)=='1' else 'NO'}")
            else:
                print("DUPLICATE PRECHECK: not confirmed")
        probe=re.search(r"COMMIT_PROBE hr=0x([0-9a-fA-F]{8}) record_seen=(\d+) bounded_template=(\d+)(?: add_calls=(\d+))?",log)
        if probe:
            print("OFFLINE COMMIT PROBE:",f"HRESULT=0x{probe.group(1)};",
                  f"record received={'YES' if probe.group(2)=='1' else 'NO'};",
                  f"bounded nonempty template={'YES' if probe.group(3)=='1' else 'NO'};",
                  f"AddRecord callbacks={probe.group(4) if probe.group(4) is not None else 'unavailable'}")
            if probe.group(1).lower() == "00000000" and probe.group(3)=="1":
                print("Mock storage received a template in memory. Matching/verification NOT ESTABLISHED.")
            else:
                print("A usable committed template was NOT demonstrated.")
        else:
            print("OFFLINE COMMIT PROBE: NOT REACHED or result UNAVAILABLE.")
        print("No biometric template persisted or saved; sandbox process has exited.")
    else:
        print("No biometric template was committed or saved.")
    return True

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive",type=Path,help="local FocalTech driver ZIP")
    ap.add_argument("--captures-dir",type=Path,
                    default=ROOT/"local-data/enroll-captures")
    ap.add_argument("--completion-from-update",action="store_true",
                    help="opt-in Windows capture workflow interpretation; stop at UpdateEnrollment S_OK, retain status as diagnostic")
    ap.add_argument("--probe-commit-in-memory",action="store_true",
                    help="after UpdateEnrollment S_OK, call engine CommitEnrollment only inside disposable sandbox/mock storage; never write templates")
    ap.add_argument("--with-duplicate-check",action="store_true",
                    help="before in-memory CommitEnrollment, invoke documented CheckForDuplicate preflight (opt-in)")
    ap.add_argument("--skip-enrollment-status",action="store_true",
                    help="skip independent status query to mimic Windows enrollment capture sequence")
    ap.add_argument("--invert-input",action="store_true",
                    help="offline test: invert PGM grayscale polarity IN MEMORY (255-value), without modifying files")
    ap.add_argument("--with-sample-hint",action="store_true",
                    help="ask vendor engine's read-only standard sample-count hint")
    ap.add_argument("--with-extended-status",action="store_true",
                    help="opt-in offline query of WinBio extended enrollment status (ABI experimental)")
    ap.add_argument("--with-enrollment-parameters",action="store_true",
                    help="opt-in offline call to standard WinBio SetEnrollmentParameters after CreateEnrollment")
    ap.add_argument("--limit",type=int,default=16,
                    help="number of existing PGM images, 2-20 (default: 16)")
    args=ap.parse_args()
    if not 2<=args.limit<=20:ap.error("--limit must be between 2 and 20")
    if (args.probe_commit_in_memory or args.skip_enrollment_status) and not args.completion_from_update:
        ap.error("--probe-commit-in-memory/--skip-enrollment-status require --completion-from-update")
    if args.with_duplicate_check and not args.probe_commit_in_memory:
        ap.error("--with-duplicate-check requires --probe-commit-in-memory")
    if not args.archive.is_file():ap.error("Driver archive not found")
    if not args.captures_dir.is_dir():ap.error("Private capture directory not found")
    files=sorted(args.captures_dir.glob("enroll_capture_*.pgm"))[:args.limit]
    if len(files)<2:ap.error("At least two existing PGM captures required")
    for path in files:
        st=path.lstat()
        if not stat.S_ISREG(st.st_mode):
            ap.error(f"Not a regular private PGM file: {path}")
    print(f"Replaying {len(files)} existing local PGM captures. No USB or new scans.")
    print("Pixel polarity:", "INVERTED (255-pixel, in-memory only)" if args.invert_input else "ORIGINAL")
    if args.probe_commit_in_memory:
        print("EXPERIMENT: Attempt CommitEnrollment into mock in-memory storage, then wipe it.")
    if args.with_duplicate_check:
        print("EXPERIMENT: Call CheckForDuplicate before CommitEnrollment, matching the Windows commit sequence.")
    if args.skip_enrollment_status:
        print("EXPERIMENT: Do not call GetEnrollmentStatus; match Windows capture callback sequence.")
    if args.completion_from_update:
        print("EXPERIMENT: Use UpdateEnrollment to decide when capture collection is ready.")
        if not args.skip_enrollment_status:
            print("GetEnrollmentStatus will also be queried for diagnostics.")
        if not args.probe_commit_in_memory:
            print("No commit will be attempted.")
    if args.with_enrollment_parameters:
        print("EXPERIMENT: SetEnrollmentParameters enabled (unknown finger subtype).")
    if args.with_extended_status:
        print("EXPERIMENT: QueryExtendedEnrollmentStatus enabled; isolated vendor DLL call.")
    if args.with_sample_hint:
        print("EXPERIMENT: QuerySampleHint enabled (read-only DLL call).")
    try:
        proc=subprocess.run(
            ["bash",str(BATCH),*(["--invert-pixels"] if args.invert_input else []),*(["--completion-from-update"] if args.completion_from_update else []),*(["--skip-enrollment-status"] if args.skip_enrollment_status else []),*(["--probe-commit-in-memory"] if args.probe_commit_in_memory else []),*(["--with-duplicate-check"] if args.with_duplicate_check else []),*(["--with-enrollment-parameters"] if args.with_enrollment_parameters else []),*(["--with-extended-status"] if args.with_extended_status else []),*(["--with-sample-hint"] if args.with_sample_hint else []),str(args.archive.resolve()),*map(str,files)],
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
    if args.with_sample_hint:
        hint=re.search(r"ENROLL_HINT query_hr=0x([0-9a-fA-F]{8}) samples=(\d+|unavailable)",proc.stderr)
        if hint:
            print("QuerySampleHint result:",f"0x{hint.group(1)}; required samples={hint.group(2)}")
        else:
            print("QuerySampleHint result: NOT CONFIRMED")
    setup=re.search(r"ENROLL_DIAG set_params_hr=0x([0-9a-fA-F]{8}) subfactor=(\d+)",proc.stderr)
    if args.with_enrollment_parameters:
        print("SetEnrollmentParameters result:",(f"0x{setup.group(1)}; subfactor={setup.group(2)}" if setup else "NOT CONFIRMED"))
    ok=summarize(proc.stderr,files,completion_from_update=args.completion_from_update,probe_commit=args.probe_commit_in_memory,skip_status=args.skip_enrollment_status,with_duplicate_check=args.with_duplicate_check)
    return 0 if ok else 1

if __name__=="__main__":
    raise SystemExit(main())
