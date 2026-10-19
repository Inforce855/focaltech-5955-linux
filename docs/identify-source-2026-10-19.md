# FT5955 two-finger identification: opt-in source-only implementation

**19 October 2026.** The user wants standard PAM \`any\` to accept either enrolled index finger without another enrolment. This is the *existing* \`focaltech_5955\` libfprint driver; the proprietary MOH engine, UID955 service and global PAM stay untouched while this source variant is evaluated.

## Source of truth and non-regression

User's read-only SHA-256 output for the three local \`~/Projects/libfprint-ft5955\` files exactly equals the immutable 16 October GitHub source manifest:

- \`focaltech_5955.c\`: \`40418e509506400a4118a35f76a0482ad614b855d285d88971e342b81ebad703\`
- \`ft5955_native_action.c\`: \`0f52c8de56f4ee524f1225bd0db559262505c21f906b4034def1e01d61ec94ab\`
- \`ft5955_native_action.h\`: \`4c7098d939e792540d82320dd9bcf2eb5899dec9571cc8172d22b9541c5629ee\`

The active \`/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0\` contains \`FT5955TIMING phase=%s mono_us=%li\` — instrumentation **absent from those source files**. The installed library came from an opt-in disposable-build transformation on the relay-latency branch. A direct rebuild from \`~/Projects/libfprint-ft5955\` would therefore regress the running driver and is prohibited.

## Opt-in changes committed on this existing branch

- \`tools/ft5955_identify_overlay.py\` adds \`dev_class->identify\` and a separate async identify worker **only inside a disposable reconstructed upstream libfprint source**. No immutable driver snapshot or installed source file changes.
- \`tools/verify_ft5955_clean_clone.py --build --trace-timing --identify\` compiles the previous validated 100-ms, early-capture, trace variant with this overlay. \`--stage --trace-timing --identify\` additionally stages the resulting library in private \`~/.local/state/ft5955-system-trial/stage-identify\` but **does not install it**. The existing privileged install script has no identify activation option.
- \`tests/test_ft5955_identify_overlay.py\` asserts registration, a single capture before a gallery search, no-match safety, unchanged verify callback, bounded retries, snapshot immutability and fail-before-write source preflight. An existing GitHub Actions offline synthetic workflow now includes these tests. **Test source contracts are not proof of real-device identification.**

Implementation uses \`fpi_device_get_identify_data()\` to obtain only libfprint-provided enrolled prints. It validates/extracts each vendor template, copies and later clears the protected bytes, captures one new finger touch, then starts one protected \`MODE V\` gateway per gallery entry using **the same captured image**. A vendor \`MATCH\` maps to the corresponding original \`FpPrint\`; genuine \`NO_MATCH\` proceeds to the next entry; quality reject requests a *fresh* touch; malformed result, backend failure, invalid template, cancelled request, forced gateway kill or empty gallery **fail closed**. No raw images or templates logged. Only the existing vendor matching process determines MATCH. Explicit \`verify\` and \`enroll\` callbacks remain unchanged. A scanned print FpPrint is not synthesized (the vendor engine provides only a verdict); libfprint match callbacks permit it to be omitted for this kind of device.

## Gates before installation

1. Run the offline source tests (NO USB), then the opt-in clean build (NO USB, NO privileged install) from the **existing relay-latency checkout** after a clean fast-forward update; do not overwrite a dirty checkout or create new worktrees.
2. Resolve compiler warnings or API mistakes against exact pinned libfprint \`v1.94.100\` headers. The resulting code is currently **uncompiled on the user's machine**, and the source-only commit is not a pass claim.
3. Prepare a guarded installation plan with an exact backup of the *currently loaded* \`/opt/ft5955-system-trial/lib\` and rollback independent of PAM; user approval is required to replace the live auth library. No changes to enrolled prints or credential files.
4. Confirm single-touch matching both left and right fingers, wrong-finger rejection, interrupted/timeout cleanup, normal password fallback and no \`AlreadyInUse\` regression in a controlled session.
5. Preserve the long-term non-\`dev\` service migration and proprietary MOH trust review; identify is not itself an authentication-security audit.

**Scope:** no PAM edits, no new branch, no changes to the already hardware-tested timing/relay source, no biometric captures during source or build tests.

## Confirmed read-only build result — 19 October 2026

**User's real Nobara output** from existing checkout `~/Projects/ft5955-relay-latency-test` (detached HEAD fast-forwarded successfully from `66e054c` to `ccfdd59`):

- `python3 -m unittest discover -s tests -p test_ft5955_identify_overlay.py -v`: **4/4 PASS**, 0.002 seconds. Tests cover overlay anchors, no changes to historical snapshot, no repeat apply, symlink rejection.
- `python3 tools/verify_ft5955_clean_clone.py --build --trace-timing --identify`: historical patch digests verified; exact upstream libfprint `v1.94.100` Git commit `80a4b5ec612892c5c056c48dddaa561452cf37ec`; all three patches applied; 100 ms polling + early-capture + nonbiometric timing trace + identify overlay applied in a disposable /tmp source; Meson 27 build targets; Ninja **109/109 PASS**; output `PASS: CLEAN upstream clone + 3 GitHub patches built independently`, followed by `PASS: disposable source and build removed; live driver, system fprintd, PAM unchanged.`
- Annotated-tag warning and skipped optional introspection-dependent tests were nonfatal. **A full runtime test suite, staging, installation and genuine two-finger identify are not yet proven.** No hardware or enrolment was accessed during build.
- The existing `tools/ft5955_kde_trial.sh` / `manage_ft5955_kde_trial.sh` are historical short-lived trial launchers, and the latter explicitly refuses activation when `fprintd-pam` is present. **Do not use them to bypass guards in this now-functional global PAM setup.** After staging, a purpose-designed reversible live installation test is needed to preserve current `/opt` driver and enrolled templates.

**Next safe step**: `python3 "$HOME/Projects/ft5955-relay-latency-test/tools/verify_ft5955_clean_clone.py" --stage --trace-timing --identify`. This will perform another isolated compile and place a user-owned output under `~/.local/state/ft5955-system-trial/stage-identify`, refusing overwrite if it exists; it will not change running `/opt` libfprint, PAM, system fprintd, MOH service or user templates. Then validate the staged SHA-256 and plan guarded backup/rollback for a real test; no direct copy into /opt and no reliance on deprecated trial launchers.


## User-verified identify staging PASS — 19 October 2026

The user's real Nobara terminal run of `python3 "$repo/tools/verify_ft5955_clean_clone.py" --stage --trace-timing --identify` completed successfully in ~4.4 seconds. GitHub snapshot source/patch manifest verified; upstream pinned libfprint v1.94.100 at `80a4b5ec`; Ninja **109/109**; the private staged library was written to `/home/tim/.local/state/ft5955-system-trial/stage-identify/lib/libfprint-2.so.2.0.0`. Staged SHA-256 reported: **`70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd`**.

The variant's own output explicitly confirms **nothing installed under `/opt`, `/etc`, or `/usr`**, and no USB, system fprintd or PAM operations. Original active library remains unchanged. No real identification performed yet. The optional introspection-dependent tests were skipped at Meson configuration and are **not** counted as passing.

**Next immediate check, read-only:** verify the staged `SHA256` manifest and file with `sha256sum -c`, record checksum and physical ownership/type of the current `/opt/ft5955-system-trial/lib/libfprint-2.so.2.0.0`, check `fprintd.service` drop-ins and live paths, then prepare reversible, guarded live swap without touching `fprintd-pam`, `authselect`, global PAM, MOH, daemon configuration or prints. Existing lab install wrappers refuse when fprintd-pam is active and must not be reused or guard-bypassed. Never blindly overwrite current binary or delete historic staged libraries.

