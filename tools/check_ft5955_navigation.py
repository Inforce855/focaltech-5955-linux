#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline, read-only relative Markdown navigation check for current project docs.

No external requests, GitHub authentication, hardware, vendor engine or system
changes. Historical research text is intentionally not rewritten/checked.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
CURRENT = (
    ROOT / "README.md",
    ROOT / "docs/index.md",
    ROOT / "docs/next-session-handoff.md",
    ROOT / "docs/roadmap.md",
    ROOT / "docs/kde-short-lived-trial-2026-10-17.md",
)
MARKDOWN_LINK = re.compile(r"\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)")


def check() -> int:
    errors: list[str] = []
    for doc in CURRENT:
        if not doc.is_file():
            errors.append(f"missing navigation source: {doc.relative_to(ROOT)}")
            continue
        contents = doc.read_text(encoding="utf-8")
        for raw in MARKDOWN_LINK.findall(contents):
            if raw.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = unquote(raw.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            candidate = (doc.parent / target).resolve()
            if not candidate.is_relative_to(ROOT.resolve()):
                errors.append(f"{doc.relative_to(ROOT)}: link escapes repository: {raw}")
            elif not candidate.exists():
                errors.append(f"{doc.relative_to(ROOT)}: broken relative link: {raw}")
    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        return 1
    print(f"PASS: local navigation links in {len(CURRENT)} current documentation files")
    print("No network, USB, fingerprints, systemd, fprintd or proprietary code involved")
    return 0


if __name__ == "__main__":
    sys.exit(check())
