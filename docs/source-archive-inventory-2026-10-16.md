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
