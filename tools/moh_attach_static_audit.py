#!/usr/bin/env python3
"""Read-only audit of the compile-time gated WinBio Attach path."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
source = (root / "engine/ft_engine.c").read_text(encoding="utf-8")
checks = [
    ("Two compile-time execution gates retained",
     "FT5955_ALLOW_UNVERIFIED_ATTACH" in source and
     "FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT" in source),
    ("Typed WinBio pipeline declared",
     "static ft5955_winbio_pipeline pipeline;" in source),
    ("SensorInterface assigned", "pipeline.sensor_interface=g_sensor_vt;" in source),
    ("EngineInterface assigned", "pipeline.engine_interface=iface;" in source),
    ("StorageInterface assigned", "pipeline.storage_interface=g_storage_vt;" in source),
    ("Unverified engine context writes removed",
     "*(u32*)(ctx+0x24)" not in source and
     "*(u32*)(ctx+0x28)" not in source),
    ("Attach still uses pipeline address", "Attach(&pipeline)" in source),
]
print("FocalTech 5955 gated Attach source audit — STATIC ONLY")
for label, passed in checks:
    print(f"{'OK' if passed else 'FAIL'}  {label}")
print("BLOCKED: Sensor/storage callback ABI and interface headers are not validated.")
print("This audit does not execute the proprietary DLL or enable Attach.")
sys.exit(0 if all(passed for _, passed in checks) else 1)
