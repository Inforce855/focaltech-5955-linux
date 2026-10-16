# FT5955 local source archive inventory — 16 October 2026

This is an **inventory**, not a source import or a claim that the current local libfprint tree has been committed. Archive inputs were shared in the conversation and inspected without executing installer scripts.

## Source bundles recovered

| Archive version | Source files | SHA-256 (uploaded archive) | Purpose |
| --- | ---: | --- | --- |
| `ft5955-driver-integration-v0.8.tar.gz` | 30 | `d3030d7ba0d26a3f167ffbfbdf4067eaf199905f7ee75de31a4e0674d6f55231` | Original libfprint native action/capture, FpPrint codec/bridge, MOH gateway, tests, guarded apply/restore |
| `ft5955-v0.8.1-fix-cleanup.py` | 1 | `fc0608e5fe15abf244d7cb109e557caad5344737227e794be5dc6be39ef681f6` | Replaces five invalid process-cleanup status checks; guarded local patch |
| `ft5955-native-validation-v0.9.tar.gz` | 5 | `b734dc99f60b1cbae18956d5138a392fe674fada5eab944fedc48374aa209e63` | Test-only real FpPrint RAM serialise/deserialize across a new libfprint device/context; A,B,C,A verification |
| `ft5955-native-validation-v0.9.1.tar.gz` | 5 | `857d445ee7dc01e11a1aa7cec3bb9cdeb4685e859e0f2784631110877fb1979f` | Test-only 10-check A/B/A/C/A/B/A/C/A/A sequence with quality-retry counts |
| `ft5955-v094-source.tar.gz` | 6 | `3762811926d28afd035241c649c27222d8ab7745f1591c4b8a84878243049a8d` | Separate v0.9.4 cancellation and forced quality retry tests, not replacement driver code |

The observed `ft5955_native_action.c` pasted from the **currently modified local libfprint checkout** was compared with v0.8 `driver/ft5955_native_action.c` after all five v0.8.1 `g_subprocess_get_if_exited(child)` to `(g_subprocess_get_identifier(child) == NULL)` substitutions. The C source **matches line-for-line**. This establishes provenance for that individual file, **not** byte parity of every other locally modified source file.

The v0.9.1 `native_print_roundtrip.c` genuinely extends the v0.9 test rather than changing the driver, adding 10 labelled comparisons, quality-retry callback and explicit counters. v0.9 results already documented a final genuine NO_MATCH after earlier expected matches and negatives. This matters when interpreting the 16 October private-fprintd restart trial: that test had a saved finger listing but three genuine terminal NO_MATCH results. The restart alone has **not** been established as the root cause, especially because no same-session verification was run immediately before restart.

## Version control status / caution

On the repository's three branches examined (`main`, `feature/ft5955-moh-engine-bridge`, `feature/ft5955-private-fprintd-v096`), the original `ft5955_native_action.[ch]` and the private driver `focaltech_5955.c` were **not present**. v0.9.4-related testing sources do already appear on the older MOH branch; compare before publishing duplicates.

These historical archives are **not yet imported as source files on this branch**. The live local driver, Meson changes and gateway may have additional modifications beyond the recovered snapshots. Before declaring a reproducible driver, inventory and review the dirty checkout with `git status`/`git diff` and reconcile those files; never overwrite the local working source or apply the old v0.8 installer/patch blindly.

Publish extracted, reviewed **text-only** historical sources in a separate source-history directory or feature branch. Never commit biometric images, real templates, raw samples, personal log dumps, proprietary vendor DLLs, compiled programs or archive duplicates. Avoid `git clean`, `git reset --hard`, forced pushes and destructive checkout operations.

See [current status](status-2026-10-16.md), [development roadmap](roadmap.md) and [source inventory issue #3](https://github.com/Inforce855/focaltech-5955-linux/issues/3).


## Additional recovered files (final batch, 16 October 2026)

These are additional **historical inputs**, not proposed replacements for the current native driver.

| Recovered upload | Contents | SHA-256 of upload | Assessment |
| --- | --- | --- | --- |
| `ft5955-moh-ipc-v0.1.tar.gz` | `moh_ipc.py`, README (2 source files) | `0a9d00af12acd8899b84e1ce94af80e619f413a802cc01003c8ed8a038334a01` | Earliest **synthetic/mock** IPC protocol; preserve as provenance, superseded by v0.2/v0.3 |
| `ft5955-moh-ipc-v0.2.tar.gz` | `moh_adapter.py`, fake vendor runner, test, README (4 files) | `4b8e91a4627a08631868520e915213d59836969472b755a8598cb5034b877db5` | Isolated MOH adapter boundary with synthetic regression tests; historical reference, not production driver |
| `focaltech-5955-live-libfprint.tar.gz` | Live bridge, isolated build/enrol scripts, test, docs (5 files) | `f349b6c311bc4f6b69173a1a98b39b114e1c54c9afa3b8fbbb37830343f14c3e` | Early virtual-image live bridge at 10×; superseded in part by scale fix |
| `focaltech-5955-libfprint-scale-fix.tar.gz` | Revised live bridge, test and docs (3 files) | `13d0ed22fc07116bad31b6375605f67ceb67fe6caf145370d0be88a34ba1bf5b` | Newer 2× interpolation default; preserve later bridge variant instead of silently overwriting earlier one |
| `focaltech-nbis-one-touch.tar.gz` | NBIS probe, one-touch diagnostic, tests, docs (5 files) | `0aeef7ab90fc57e0582cdc47b02a2381c75393892ac978ef091e128bc5d3a450` | Distinct minutiae-extraction diagnostic; useful to understand why generic libfprint NBIS path struggled |
| `fix_focaltech_5955_scaffold.py` | Early libfprint 1.94.100 registration and discovery-only stub | `92cb5358aaad44044b4dc3f9469637598a1e470f2bf39253f3868eaf0a70eedb` | **Obsolete as an installer**; source preserved at [scaffold repair](../research/source-history/scaffold/fix_focaltech_5955_scaffold.py). Do **not run** on live tree |
| `moh-attach-disassembly.txt` | Audited vendor Attach disassembly research note | `7072f6470f5c3b6aeddf49d08b51db414b12fbcc4e939057b95e61536143cc43` | Historical analysis only; proprietary-derived disassembly not imported as repository source without licensing review |

The real source of the historical v0.8.1 process-cleanup change is now preserved separately at [v0.8.1 patch script](../research/source-history/v0.8.1/ft5955-v0.8.1-fix-cleanup.py). It is **not** an instruction to reapply a patch to the currently working local driver.

## Source consolidation gate

Before marking the repository as the **authoritative rebuildable native driver**, the original **local** `~/Projects/libfprint-ft5955` driver files, private Meson registrations, `~/Projects/ft5955-driver-integration-v0.8/engine` gateway and dependency manifests must be compared with these historical archives and imported under reviewed version control. Preserve active development work, prefer source files over gz archive copies, and avoid storing biometric or proprietary vendor materials. Current source archives are inventoried but **not yet completely imported**. The two standalone Python patch scripts above were committed; no hardware files or auth setup were changed.


## Non-destructive import helper (committed; not run on user's PC)

The repository now contains [`tools/import_ft5955_history.py`](../tools/import_ft5955_history.py). It recognises the **10 listed historical source archives by SHA-256**, reads only bounded regular UTF-8 source files from those archives, rejects links/unsafe paths, and lays out their files in version-specific `research/source-history/` directories. This keeps overlapping versions separate and does not run old installers.

The **dry-run was tested against all ten uploaded archives** in the assistant's isolated environment: **68 text source files** recognised. The importer has not been run on the user's Nobara checkout. It refuses to stage unless the checkout is clean and checked out on `feature/ft5955-private-fprintd-v096`; it refuses overwrites and does not make commits or push. It never touches `~/Projects/libfprint-ft5955`.

Example **read-only** use from any checked-out copy of the repository, after fetching the current feature branch:

```bash
python3 tools/import_ft5955_history.py "$HOME/Downloads"
```

Opt-in `--stage` should only follow review of the worktree and branch. The user must inspect the staged source and explicitly commit/push the imported files separately. **A full historical source import is not yet confirmed on GitHub.**

