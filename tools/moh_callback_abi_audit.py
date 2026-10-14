#!/usr/bin/env python3
"""Static inspection of gated MOH sensor/storage WinBio table wiring."""
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
src=(root/"engine/ft_engine.c").read_text()
hdr=(root/"engine/ft5955_winbio_interface_probe.h").read_text()
checks=[
 ("Header-bearing storage table", "static ft5955_winbio_interface_probe g_storage_vt;" in src),
 ("Header-bearing sensor table", "static ft5955_winbio_interface_probe g_sensor_vt;" in src),
 ("Sensor header initialised", "ft5955_winbio_interface_probe_init(&g_sensor_vt" in src),
 ("Storage header initialised", "ft5955_winbio_interface_probe_init(&g_storage_vt" in src),
 ("Pointers begin after 0x20 header", "FT5955_SLOT(offset) (((offset)-0x20u)/8u)" in src),
 ("Unimplemented callback fails closed", "ft5955_unimplemented_callback" in src),
 ("Pipeline points to header beginnings",
  "pipeline.sensor_interface=&g_sensor_vt;" in src and
  "pipeline.storage_interface=&g_storage_vt;" in src),
 ("Header size and callback position enforced",
  "_Static_assert(sizeof(ft5955_winbio_interface_probe)==0x100u" in hdr and
  "_Static_assert(offsetof(ft5955_winbio_interface_probe,slots)==0x20u" in hdr),
]
print("5955 WinBio callback-table wiring audit — STATIC ONLY")
for label,ok in checks:
 print(f"{'OK' if ok else 'FAIL'}  {label}")
print("BLOCKED: Version negotiation, adapter GUIDs and per-slot callback ABI")
print("are not yet validated. This audit does not enable Attach.")
sys.exit(0 if all(ok for _,ok in checks) else 1)
