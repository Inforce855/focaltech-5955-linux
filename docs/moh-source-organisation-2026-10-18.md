# MOH source organisation — 18 October 2026

## Goal

Preserve all previous FocalTech 5955 research, but separate the code necessary to reproduce the **already-working** real MOH matcher from historical diagnostics. This is a **classification**, not a refactor, move or deletion.

### Four groups

1. **DIRECT_BUILD:** `.c` inputs explicitly named by the working `tools/test_moh_isolated_live_identify.sh` GCC invocation. These are required to reproduce that command.
2. **LAUNCH_SECURITY:** the known shell launcher and `moh_engine_preflight.py` which checks the pinned vendor DLL/imports. These must be retained and audited as a unit.
3. **ENGINE_DEPENDENCY_REVIEW:** the rest of `engine/*.c` and `engine/*.h`. This is **not** an optional category: directly compiled C may `#include` these headers, and other C modules may need linkage. Do not remove them until the exact compiler dependency graph and build are verified.
4. **HISTORICAL_DIAGNOSTIC:** other `tools/*.c` research probes and tests that the current main GCC command does not invoke. Keep in source control, even if not deployed to the service.

## Reproducible inventory

`python3 -B tools/classify_ft5955_moh_sources.py` (run against the user's original MOH checkout) reads only source text and prints the four categories. It does **not** compile, invoke the DLL, move files or install anything.

The user's previous source-only inventory reported 58 candidate files. The classification script determines actual per-group counts at runtime from the working launcher; **do not assume** that all 58 files belong in the installed runtime.

## Proved on Nobara

- Independent synthetic service account `ft5955-engine` UID 955 exists and development socket/service are active.
- User socket attempt was denied by kernel permissions; root connected and received `ERROR DEV_ONLY_NO_AUTH`.
- The first three staged MOH source files matched originals by SHA-256. The staging was deliberately partial.
- Original user-session matching continues to function in its separate live trial; no PAM changes.
- **No real MOH engine has yet run as UID 955.** Current dev service always refuses authentication.

## Next engineering gates

- Obtain categories and exact direct-build source list from the classification script.
- Derive transitive includes; stage only a complete and hash-verified build closure in the distinct `/opt/ft5955-dev` tree.
- Test compiler and launcher preflight in a non-authentication environment.
- Resolve UID 955 sandbox constraints **without** repeating the already-failed nested-bwrap experiment or weakening protections without review.
- Secure persistent templates and match result origin before ever changing PAM.

Do not modify the immutable driver snapshot or the 110-import check; do not delete any historical test files.
