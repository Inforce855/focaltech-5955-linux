#!/usr/bin/env python3
"""Repair/check a local libfprint 1.94.100 FocalTech 5955 discovery scaffold.

Only edits files in the checkout named on the command line. Does not install or
run anything, access USB, modify system auth, or handle fingerprint data.
"""
from pathlib import Path
import sys

SOURCE = '/* SPDX-License-Identifier: LGPL-2.1-or-later\n * FocalTech 2808:5955 — experimental discovery-only scaffold.\n *\n * Hardware I/O, enrollment, verification and the isolated MOH bridge are\n * deliberately NOT wired up.  Never install this prototype into the system\n * libfprint/fprintd authentication stack.\n */\n#define FP_COMPONENT "focaltech_5955"\n#include "drivers_api.h"\n\nstruct _FpiDeviceFocaltech5955\n{\n  FpDevice parent;\n};\n\nG_DECLARE_FINAL_TYPE (FpiDeviceFocaltech5955, fpi_device_focaltech_5955,\n                      FPI, DEVICE_FOCALTECH_5955, FpDevice);\nG_DEFINE_TYPE (FpiDeviceFocaltech5955, fpi_device_focaltech_5955, FP_TYPE_DEVICE);\n\nstatic const FpIdEntry id_table[] = {\n  { .vid = 0x2808, .pid = 0x5955 },\n  { .vid = 0 },\n};\n\nstatic void\nfocaltech_5955_open (FpDevice *dev)\n{\n  /* Fail safely until a real USB open/capture path is implemented. */\n  fpi_device_open_complete (dev, fpi_device_error_new_msg (\n      FP_DEVICE_ERROR_NOT_SUPPORTED, "5955 driver is discovery-only"));\n}\n\nstatic void\nfocaltech_5955_close (FpDevice *dev)\n{\n  fpi_device_close_complete (dev, NULL);\n}\n\nstatic void\nfpi_device_focaltech_5955_init (FpiDeviceFocaltech5955 *self)\n{\n  (void) self;\n}\n\nstatic void\nfpi_device_focaltech_5955_class_init (FpiDeviceFocaltech5955Class *klass)\n{\n  FpDeviceClass *dev_class = FP_DEVICE_CLASS (klass);\n\n  dev_class->id = FP_COMPONENT;\n  dev_class->full_name = "FocalTech 2808:5955 (experimental discovery only)";\n  dev_class->type = FP_DEVICE_TYPE_USB;\n  dev_class->id_table = id_table;\n  dev_class->nr_enroll_stages = 12;\n  dev_class->open = focaltech_5955_open;\n  dev_class->close = focaltech_5955_close;\n\n  fpi_device_class_auto_initialize_features (dev_class);\n}\n'


def add_entry(text: str, needle: str, entry: str, location: str) -> tuple[str, str]:
    if entry in text:
        return text, f"{location}: already registered"
    if text.count(needle) != 1:
        raise ValueError(
            f"{location}: expected one known FocalTech MOC insertion point; "
            f"found {text.count(needle)} (nothing changed)"
        )
    return text.replace(needle, needle + entry, 1), f"{location}: added registration"


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "~/Projects/libfprint-ft5955").expanduser().resolve()
    top = root / "meson.build"
    lib = root / "libfprint/meson.build"
    driver = root / "libfprint/drivers/focaltech_5955.c"
    if not (root / ".git").is_dir() or not top.is_file() or not lib.is_file():
        raise ValueError(f"Not an existing libfprint checkout: {root}")
    t = top.read_text()
    l = lib.read_text()
    if "1.94.100" not in t:
        raise ValueError("Expected libfprint 1.94.100; refusing to patch an unknown version")

    # Only alter the default_drivers list; the same MOC name can occur elsewhere.
    start = t.find("default_drivers = [")
    end = t.find("]", start) if start >= 0 else -1
    if start == -1 or end == -1:
        raise ValueError("Cannot locate default_drivers list")
    section = t[start:end]
    changed_section, top_info = add_entry(
        section,
        "    'focaltech_moc',\n",
        "    'focaltech_5955',\n",
        "meson.build default_drivers",
    )
    new_t = t[:start] + changed_section + t[end:]

    # The error at libfprint/meson.build:157 is from this dictionary being
    # missing the new key. Insist it is inside driver_sources, not elsewhere.
    block_start = l.find("driver_sources = {")
    block_end = l.find("\n}", block_start) if block_start >= 0 else -1
    if block_start == -1 or block_end == -1:
        raise ValueError("Cannot locate driver_sources dictionary")
    block = l[block_start:block_end + 1]
    changed_block, lib_info = add_entry(
        block,
        "    'focaltech_moc' : files('drivers/focaltech_moc/focaltech_moc.c'),\n",
        "    'focaltech_5955' : files('drivers/focaltech_5955.c'),\n",
        "libfprint/meson.build driver_sources",
    )
    new_l = l[:block_start] + changed_block + l[block_end + 1:]

    if driver.exists():
        d = driver.read_text()
        if 'fpi_device_focaltech_5955' not in d or '.pid = 0x5955' not in d:
            raise ValueError("Existing focaltech_5955.c is unexpected: leaving all files unchanged")
        driver_info = "focaltech_5955.c: already present"
    else:
        driver_info = "focaltech_5955.c: created discovery-only scaffold"

    # Finished all checks; now apply the edits (idempotently).
    if not driver.exists():
        driver.write_text(SOURCE)
    if new_t != t:
        top.write_text(new_t)
    if new_l != l:
        lib.write_text(new_l)
    print(top_info)
    print(lib_info)
    print(driver_info)
    print("Scaffold registration repaired; no system changes made.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
