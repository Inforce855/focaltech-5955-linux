#!/usr/bin/env python3
"""Read-only import compatibility check for the verified 5955 MOH matching DLL.

Accepts the original private driver ZIP or an extracted MOH engine DLL.
Does not execute the Windows DLL, capture images, or access USB.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

PIN = "a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c"
IMPORT = re.compile(r"^\s*[0-9A-Fa-f]+\s+<none>\s+[0-9A-Fa-f]+\s+(\S+)")
DLL = re.compile(r"^\s*DLL Name:\s+(\S+)")
R = re.compile(r"\bR\(([A-Za-z_]\w*)\)")
REG = re.compile(r'\breg\(\s*"([A-Za-z_]\w*)"\s*,')

def imports_from_objdump(text):
    result = []
    inside, library = False, None
    for line in text.splitlines():
        if line.startswith("The Import Tables"):
            inside = True
            continue
        if inside and line.startswith("The Export Tables"):
            break
        if not inside:
            continue
        m = DLL.match(line)
        if m:
            library = m.group(1)
        else:
            m = IMPORT.match(line)
            if m and library:
                result.append((library, m.group(1)))
    return result

def registered_shims(source):
    return (set(R.findall(source)) - {"n"}) | set(REG.findall(source))

def audit(dll, source):
    if not dll.is_file() or dll.is_symlink():
        raise ValueError("DLL must be a local regular file, not a symlink")
    with dll.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != PIN:
        raise ValueError("DLL hash mismatch: this is not the verified 5955 MOH engine")
    output = subprocess.run(["objdump", "-p", str(dll)], check=True,
                            capture_output=True, text=True, timeout=30).stdout
    imported = imports_from_objdump(output)
    if not imported:
        raise ValueError("Could not extract named DLL imports")
    shim_names = registered_shims(source.read_text(encoding="utf-8"))
    missing = [(lib, func) for lib, func in imported if func not in shim_names]
    return len(imported), Counter(lib for lib, _ in imported), len(shim_names), missing

def archive_engine(archive, directory):
    with zipfile.ZipFile(archive) as z:
        paths = [p for p in z.namelist()
                 if "/MOH/" in p and p.endswith("/ftWbioEngineAdapter.dll")]
        if len(paths) != 1 or z.getinfo(paths[0]).file_size > 4000000:
            raise ValueError("Expected exactly one appropriately sized MOH engine DLL")
        result = directory / "ftWbioEngineAdapter.dll"
        with result.open("xb") as dest:
            dest.write(z.read(paths[0]))
        result.chmod(0o600)
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path, help="private MOH DLL or 7_Fingerprint-module.zip")
    parser.add_argument("--source", type=Path,
                        default=Path(__file__).resolve().parents[1] / "engine" / "ft_engine.c")
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="ft5955-moh-") as temp:
            dll = archive_engine(args.dll, Path(temp)) if args.dll.suffix.lower() == ".zip" else args.dll
            total, libs, num_shims, missing = audit(dll, args.source)
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(f"Preflight failed: {exc}", file=sys.stderr)
        return 2
    print("Verified 5955 MOH matching engine; static import comparison")
    print(f"Named imports: {total}")
    for lib, count in sorted(libs.items()):
        print(f"  {lib}: {count}")
    print(f"Registered loader shim names: {num_shims}")
    print(f"Covered: {total - len(missing)}/{total}; missing: {len(missing)}")
    for lib, func in missing:
        print(f"MISSING {lib}!{func}")
    print("DLL not executed; no USB or biometrics accessed.")
    if missing:
        print("BLOCKED: missing shims must be implemented and reviewed first.")
        return 1
    print("Names covered; WinBio ABI and shim behavior are not yet verified.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
