#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify existing MOH source files without moving or executing anything.

Working shell launcher's GCC command is authoritative for direct .c inputs.
Other engine headers/sources remain dependencies pending compilation review.
"""
import argparse
from pathlib import Path
import re
import shlex
import sys

def classify(root):
    script=root/"tools/test_moh_isolated_live_identify.sh"
    if script.is_symlink() or not script.is_file():
        raise ValueError("known working MOH launcher unavailable")
    lines=script.read_text().splitlines()
    build=[]
    collecting=False
    for line in lines:
        stripped=line.strip()
        if not collecting and re.match(r"^gcc\s",stripped):
            collecting=True
        if collecting:
            build.append(stripped.removesuffix("\\").strip())
            if not stripped.endswith("\\"):
                break
    if not build:
        raise ValueError("GCC invocation not found")
    command=" ".join(build)
    # Extract explicit source paths lexically; never invoke or evaluate shell.
    sources=set(re.findall(r"(?:engine|tools)/[A-Za-z0-9_.-]+\.c",command))
    if "engine/ft_engine.c" not in sources or "tools/moh_engine_live_identify.c" not in sources:
        raise ValueError("unrecognized GCC input set")
    records=[]
    for sub in ("engine","tools"):
        for p in sorted((root/sub).glob("*")):
            if p.suffix not in (".c",".h") and p.name not in (
                "moh_engine_preflight.py","test_moh_isolated_live_identify.sh"):
                continue
            if p.is_symlink() or not p.is_file():
                raise ValueError(f"symlink/non-file encountered: {p}")
            name=p.relative_to(root).as_posix()
            if name in sources:
                category="DIRECT_BUILD"
            elif name in ("tools/moh_engine_preflight.py","tools/test_moh_isolated_live_identify.sh"):
                category="LAUNCH_SECURITY"
            elif sub=="engine":
                category="ENGINE_DEPENDENCY_REVIEW"
            else:
                category="HISTORICAL_DIAGNOSTIC"
            records.append((category,name))
    for s in sources:
        if not (root/s).is_file():
            raise ValueError(f"missing direct build source: {s}")
    return sorted(records)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path.home()/"Projects/focaltech-5955-moh-test")
    a=p.parse_args()
    try:
        records=classify(a.root)
    except (ValueError,OSError) as exc:
        print("BLOCKER:",exc,file=sys.stderr)
        return 2
    for cat in ("DIRECT_BUILD","LAUNCH_SECURITY","ENGINE_DEPENDENCY_REVIEW","HISTORICAL_DIAGNOSTIC"):
        names=[name for c,name in records if c==cat]
        print(f"=== {cat}: {len(names)} ===")
        for name in names:print(name)
    print(f"TOTAL: {len(records)}. Source inventory only; no files moved, deleted or executed.")
    print("ENGINE_DEPENDENCY_REVIEW is NOT optional: headers and helper C files may be mandatory.")
    return 0
if __name__=="__main__":
    sys.exit(main())
