#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inventory the exact real MOH build closure before staging it.

Read-only. Fail closed on paths leaving original tree, symlinks, non-files.
Does not run GCC, bwrap, vendor DLL, PAM or fprintd.
"""
import argparse
from pathlib import Path
import re
import sys

SRC_SUFFIX={".c",".h"}
def inventory(root:Path):
    if root.is_symlink() or not root.is_dir():
        raise ValueError("MOH source root missing or symlink")
    # Real runner uses -Iengine and explicit C sources in gcc command.
    # Include the entire engine C/header module and tools C probe, not only
    # the three initially staged files. Python packages for import preflight.
    candidates=[p for sub in ("engine","tools") for p in (root/sub).rglob("*")
                if p.suffix in SRC_SUFFIX or (p.name=="moh_engine_preflight.py")
                or (p.name=="test_moh_isolated_live_identify.sh")]
    outputs=[]
    for p in sorted(set(candidates)):
        rel=p.relative_to(root)
        if p.is_symlink() or not p.is_file() or p.resolve().is_relative_to(root.resolve()) is False:
            raise ValueError(f"untrusted source: {rel}")
        outputs.append(rel)
    essentials=["engine/ft_engine.c","engine/ft5955_compat_time.c",
                "tools/moh_engine_live_identify.c",
                "tools/moh_engine_preflight.py",
                "tools/test_moh_isolated_live_identify.sh"]
    for item in essentials:
        if Path(item) not in outputs:
            raise ValueError(f"missing essential {item}")
    return outputs

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source",type=Path,default=Path.home()/"Projects/focaltech-5955-moh-test")
    args=a.parse_args()
    try: paths=inventory(args.source)
    except (ValueError,OSError) as exc:
        print(f"BLOCKER: {exc}");return 1
    print(f"MOH source build-closure candidates: {len(paths)}")
    for path in paths: print(path)
    print("READ-ONLY PASS: candidate inventory; compiler/sandbox/runtime NOT validated")
    return 0

if __name__=="__main__":sys.exit(main())
