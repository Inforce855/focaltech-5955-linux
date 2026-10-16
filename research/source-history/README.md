# FocalTech FT5955 — historical source snapshots

This folder preserves the individual **text source files** recovered from the development archives, in **separate versioned directories**. It is a historical record, **not** the current source tree for building or installing the active libfprint driver.

## Scope

**Imported and verified on GitHub, 16 October 2026:** Commit [`0f6e826`](https://github.com/Inforce855/focaltech-5955-linux/commit/0f6e826) added **135 historical source files across 16 version-specific directories**. The user-side importer recognised 17 archive copies (one v0.9.4 archive was duplicated), ignored four other archives, and skipped two compiled Python cache (`.pyc`) files. The repository's versioned source directories were independently confirmed through the GitHub tree listing. Proprietary/system binaries (`.so`, `.deb`, `.install`), raw biometric data and vendor disassembly were not part of this source-only import. Earlier versions remain separated by their source-history directory.

- **v0.1–v0.3:** MOH IPC and early real-capture integration.
- **v0.4–v0.7:** template restart, FpPrint codec, libfprint serialization and callback tests.
- **v0.8:** native driver components, MOH gateway and standalone integration tests.
- **v0.9–v0.9.4:** verification, cancellation, repeatability and quality-control tests.
- **Private-fprintd v0.9.6:** maintained independently in `experiments/private-fprintd/` (not part of the 135 imported archive source files).
- **Other:** live libfprint image-bridge prototypes, NBIS diagnostic, and an older Meson/driver source snapshot.

Old installer and patch scripts inside these history folders must **not** be run against the live `~/Projects/libfprint-ft5955` checkout. The old source alone is **not proof of a reproducible working current driver**.

## Import procedure

A hash-verified [source importer](../../tools/import_ft5955_history.py) checks known archive contents, skips compiled cache, and refuses to overwrite conflicting paths. By default it is read-only; `--publish` requires a clean checkout of the dedicated `feature/ft5955-source-history` branch and commits/pushes only this history folder.

The current driver must eventually be copied from the active local checkout into GitHub **after** reconciling its uncommitted state and the required build/gateway dependencies. Do not publish fingerprints, templates, proprietary DLLs or device log dumps.
