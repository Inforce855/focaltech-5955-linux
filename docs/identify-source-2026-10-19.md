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
