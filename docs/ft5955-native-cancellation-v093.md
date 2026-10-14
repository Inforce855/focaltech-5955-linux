# FT5955 v0.9.3 — cancellation diagnostic (not driver changes)

This is a **separate, opt-in, private-libfprint test client**. Its purpose is to validate operation cancellation and subsequent reader reopen **before** changing the working driver. The source and build script are:

- `tools/ft5955_cancel_probe_v093.c`
- `tools/build_ft5955_cancel_probe_v093.sh`

No production libfprint, fingerprint authentication, PAM, fprintd, system library, privilege settings or USB protocol is installed or modified. All incomplete enrolment data stays in memory and is not saved. This tool does **not** test actual fingerprint matching or guarantee vendor sandbox process cleanup. It must be run as the ordinary desktop user.

## Use with the existing v0.9.1 validation directory

Start from the research Git worktree containing the feature branch (normally `~/Projects/focaltech-5955-moh-test`); **fetch only**, do not switch branches or pull into a worktree containing unrelated changes.

```bash
(
  set -e
  cd ~/Projects/focaltech-5955-moh-test
  git fetch origin feature/ft5955-moh-engine-bridge

  TARGET="$HOME/Projects/ft5955-native-validation-v0.9.1"
  test -d "$TARGET/tests"
  test ! -e "$TARGET/tests/cancel_probe_v093.c"
  test ! -e "$TARGET/build_cancel_probe_v093.sh"
  git show FETCH_HEAD:tools/ft5955_cancel_probe_v093.c > "$TARGET/tests/cancel_probe_v093.c"
  git show FETCH_HEAD:tools/build_ft5955_cancel_probe_v093.sh > "$TARGET/build_cancel_probe_v093.sh"
  cd "$TARGET"
  bash -n build_cancel_probe_v093.sh
  bash build_cancel_probe_v093.sh
)
```
The subshell preserves the current interactive shell and refuses to overwrite previously copied v0.9.3 files.

The build script refuses root, requires an existing **private** libfprint header/library and verifies the resulting binary links to the private library. It does not compile/reinstall the driver and never runs sudo.

### Test 1: cancellation while idle (no fingerprint touch)

```bash
ulimit -c 0
export FT5955_EXPERIMENTAL_ENABLE=1
export FT5955_ENGINE_GATEWAY="$HOME/Projects/ft5955-driver-integration-v0.8/engine/engine_gateway.py"
./build-tests/cancel_probe_v093 --live-no-touch
```

Remove your finger before pressing Enter and keep it off. After about three seconds, the client calls `g_cancellable_cancel()`. It passes **only** if the async libfprint enrolment operation finishes with `G_IO_ERROR_CANCELLED`, accepts zero impressions, and the same reader closes and reopens successfully.

### Test 2: cancellation after one accepted impression

```bash
./build-tests/cancel_probe_v093 --live-after-one
```

Press Enter, touch once with a finger, then lift fully. The first accepted impression triggers cancellation automatically via an idle callback, avoiding re-entrant cancellation inside the progress callback. Rejected touches can be repeated until one is accepted. It passes **only** if the async operation terminates as cancelled, there is exactly **one** accepted impression, and the device closes/reopens. There is no need to complete twelve impressions and **no fingerprint template is persisted**.

### Results and restrictions

- A failure to cancel, failure to reopen, an unexpected completion, or an unexpected impression count is a failure, never silently converted into a pass.
- A watchdog reports failure and skips close/reopen if completion is still pending; inspect remaining gateway/bwrap processes manually before another live attempt.
- A passing close/reopen check does **not** prove there are no orphan children; follow with an operating-system process check.
- No matching thresholds, quality rejection counts, Windows MOH engine code, source-tree driver files, or system authentication settings are changed.
- This diagnostic only tests enrolment cancellation. The verification **quality-retry path** fixed in v0.9.2 still needs a separately controlled test; cancellation during verify requires an in-memory enrolled print and is a follow-up.
- Not suitable for enabling fprintd/PAM; no login-security claims.

### Limitations of offline validation

The client and script have been prepared for the user's Nobara **private libfprint v1.94.100** environment. A live USB/device test and compilation against that local libfprint build must be performed on the user's machine; publishing code and running static checks elsewhere do not establish a pass.
