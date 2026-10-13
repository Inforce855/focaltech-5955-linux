#!/usr/bin/env python3
"""Read-only checklist for the gated 5955 WinBio Attach path.

Static source audit only: never opens a DLL, USB device or biometric sample.
"""
from pathlib import Path
import re
import sys

root=Path(__file__).resolve().parents[1]
source=(root/"engine/ft_engine.c").read_text(encoding="utf-8")
checks=[
 ("Engine interface version 6.0 observed", "Observed in the isolated run (not established statically)", None),
 ("Attach gate requires TWO opt-in defines",
  "FT5955_ALLOW_UNVERIFIED_ATTACH" in source and
  "FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT" in source, "gate"),
 ("Legacy 1024-byte pipeline", bool(re.search(r"static\s+u8\s+pipeline\[1024\]",source)), "review"),
 ("Legacy storage vtable at pipeline+0x28", "pipeline+0x28" in source, "review"),
 ("Legacy sensor vtable at pipeline+0x20", "pipeline+0x20" in source, "review"),
 ("Legacy context at pipeline+0x38", "pipeline+0x38" in source, "review"),
 ("Unverified context writes +0x24 / +0x28", "ctx+0x24" in source and "ctx+0x28" in source,"review"),
 ("Legacy default callback returns success", bool(re.search(r"st_default\([^\n]*return 0;",source)), "review"),
 ("Legacy Attach invocation present", "Attach(pipeline)" in source, "review"),
]
print("FocalTech 5955 WinBio Attach preflight — STATIC ONLY")
print("No DLL execution, USB access, templates, or biometrics.")
for label,result,kind in checks:
    if kind is None: print(f"INFO  {label}: {result}")
    else: print(f"{'REVIEW' if kind=='review' and result else 'OK' if result else 'MISSING'}  {label}")
print("RESULT: Attach remains blocked. Interface pointer validation does not")
print("establish pipeline or callback ABI compatibility.")
sys.exit(0 if checks[1][1] else 1)
