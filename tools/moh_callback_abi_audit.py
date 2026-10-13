#!/usr/bin/env python3
"""Static audit of inherited sensor/storage callback-table assumptions.

This deliberately does not execute Attach or initialise any USB device.
It reports which vtable slots are currently synthetic and where the
unverified FT9201 implementation returns success for unknown methods.
"""
from pathlib import Path
import re

source=(Path(__file__).resolve().parents[1]/"engine"/"ft_engine.c").read_text()
def check(label,expression):
    print(f"{'FOUND' if expression else 'MISSING'}  {label}")
    return bool(expression)

print("FT5955 WinBio callback ABI audit — static only")
checks=[
check("Storage vtable 0x100 bytes", "g_storage_vt[0x100/8]" in source),
check("Sensor vtable 0x100 bytes", "g_sensor_vt[0x100/8]" in source),
check("Storage AddRecord +0x68", 'g_storage_vt[0x68/8]' in source),
check("Storage QueryBySubject +0x78", 'g_storage_vt[0x78/8]' in source),
check("Storage FirstRecord +0x90", 'g_storage_vt[0x90/8]' in source),
check("Storage NextRecord +0x98", 'g_storage_vt[0x98/8]' in source),
check("Storage GetCurrentRecord +0xa0", 'g_storage_vt[0xa0/8]' in source),
check("Unverified default returns success", bool(re.search(r"st_default\([^\n]*return 0;",source))),
check("Unverified sensor callbacks use default", 'g_sensor_vt[i]=(u64)st_default' in source),
]
print()
print("STATUS: UNSAFE FOR ATTACH — the default callback returns zero,")
print("and sensor/storage interface headers are not initialised or audited.")
print("Next implementation: typed fail-closed callbacks, validated interface")
print("headers, and contract tests. This script does not assert ABI correctness.")
raise SystemExit(0 if all(checks) else 1)
