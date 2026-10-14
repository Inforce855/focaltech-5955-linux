# Standard Linux enrolment: libfprint + fprintd integration

**Architecture decision — 14 October 2026:** Do **not** build or ship a separate FocalTech-specific enrolment database, enrolment GUI or authentication stack. Implement `2808:5955` support as a **libfprint device driver**, so **fprintd** and its existing Linux clients handle enrolment, verification, identification requests and user-facing progress.

The existing `tools/interactive_enroll_gui.py` and `tools/live_finger_identify.py` are **diagnostic reference programs only**, retained to reproduce the working hardware / isolated matching-engine sequence. These diagnostics now default to the separately installed, root-owned `/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll` (verified SHA-256: `a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c`). The source passes SHA-256/import checks and the temporary copy receives an additional SHA-256 check before bubblewrap launches it; the optional ZIP/DLL overrides remain usable. **libfprint/fprintd integration does not yet load this DLL or have a working driver.**

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| `fprintd` | System D-Bus API, user/session enrolment operations, known-finger labels, print storage and management; supplies `fprintd-enroll`, `fprintd-verify`, `fprintd-list`, `fprintd-delete` |
| `libfprint` | Fingerprint-device discovery and driver API; enrolment-stage progress, retry events, verify and identify results, `FpPrint` representation and serialisation |
| New `2808:5955` `libfprint` driver | Model-specific USB protocol, actual 12 accepted impressions per enrolment, release/press management, conversion to engine input, host-side template creation and matching, cleanup and cancellation |
| Research-only matcher adapter | Initially may reuse the proven **isolated proprietary FocalTech MOH engine** as a temporary, private local development reference; replace it with native free-software matching before claiming a fully open-source solution |

**Important:** Merely installing `fprintd` does not make unsupported USB VID:PID `2808:5955` work. The normal libfprint driver set must be extended (and a development build exercised) before fprintd can enumerate our device. A random external file placed next to the installed libfprint library is not an established driver plug-in mechanism: libfprint builds drivers into its library.

## Recommended implementation: custom `FpDevice` driver first

The current working matcher builds templates and compares **host-processed** samples, rather than giving libfprint a tested conventional minutiae image. A custom `FpDevice` driver with host-side verification makes fewer unverified assumptions than presenting the 64×80 image to generic NBIS matching via `FpImageDevice`.

1. **Discovery/open/close:** register `0x2808:0x5955`; reuse audited 5955 USB control and capture framing, reject unsupported devices, release resources on cancellation and close.
2. **Enrolment:** set 12 stages with `fpi_device_set_nr_enroll_stages()`; use the fresh-touch bounded scan protocol; report successful and rejected captures through `fpi_device_enroll_progress()` without advancing for bad impressions; complete through `fpi_device_enroll_complete()` with a driver-compatible `FpPrint`.
3. **Templates:** hold the candidate template privately until commit. The result needs a safe driver-specific `FpPrint` representation with matching version/algorithm metadata; `fprintd` can then manage enrolments with normal `FpPrint` serialisation. Do **not** persist proprietary DLL pointers, raw scan images or mock-process identities. Carefully assess storage permissions and the sensitivity of saved templates; fprintd storage is not a replacement for an explicit privacy review.
4. **Verification/identification:** read a *fresh* finger press, convert it the same way used for enrolment, invoke matcher against the supplied `FpPrint`(s), return results via `fpi_device_verify_report()` / `fpi_device_identify_report()`; distinguish no-match, retry/bad capture, ambiguous match and unexpected engine error. Finish operations through libfprint completion callbacks.
5. **Recoverability:** use libfprint cancellation and timeout facilities, report finger presence/release appropriately, and avoid indefinite loops, background polling after close or changes to the system login stack.

The observed 12-stages-vs-8-touches issue belongs **inside** this driver: the current eight-touch cap is per privileged diagnostic helper invocation, not a requirement of libfprint. The new driver must instead track 12 *accepted* enrolment impressions, enforce explicit overall bounds and provide normal progress/retry feedback.

## Staged testing — do not replace the system fingerprint stack yet

- **Stage A: test harness and discovery.** Add a `libfprint` source-tree driver skeleton, map VID:PID and compile in a private development prefix; test open/close and enumeration using a synthetic or mocked backend. Do not install it over Nobara's system library.
- **Stage B: real capture/progress.** Demonstrate the standard libfprint asynchronous enrolment sequence and retries using existing reader commands; abort safely, preserve privacy and return a valid serialisable `FpPrint`.
- **Stage C: verify/identify and storage.** Test true matching against multiple stored `FpPrint`s, repeated sessions and other fingers; prove template reload/version compatibility and cleanup.
- **Stage D: fprintd integration.** Test with a dedicated development fprintd/libfprint setup, isolated from production login where feasible, before replacing any system packages. Use `fprintd-enroll -f right-index-finger`, `fprintd-verify -f right-index-finger`, `fprintd-list "$USER"` and `fprintd-delete "$USER"`.
- **Stage E: optional desktop/PAM.** Only after demonstrated reliability/security and a recoverable password-login path; **do not** change PAM or KDE now.

## Remaining technical and security questions

- The working Windows MOH engine runs inside an ephemeral `bubblewrap` process; the test-only storage callback accepts a single record. A persistent `FpPrint` format and safe import/matching path across process boundaries are **not yet implemented or validated**. This is a real engineering blocker, not a GUI problem.
- Full open-source support requires replacing the proprietary Windows engine with independently developed and validated native matching. The first `libfprint` prototype may use a **private** vendor reference solely to compare behaviour, subject to isolation and licensing limits. Do not package or commit that DLL.
- Do not enable system `fprintd` enrolment before the device driver has passed controlled discovery, enrol/verify, cancellation and persistent-template tests.
- Support for other FocalTech USB/SPI models requires separate hardware/protocol validation rather than adding IDs blindly.

## Sources (upstream API documentation)

- [libfprint: Internal FpDevice and enrol/verify/identify callbacks](https://fprint.freedesktop.org/libfprint-dev/libfprint-2-Internal-FpDevice.html)
- [libfprint: FpPrint and serialisation](https://fprint.freedesktop.org/libfprint-dev/FpPrint.html)
- [libfprint: FpDevice enrolment API](https://fprint.freedesktop.org/libfprint-dev/FpDevice.html)
- [fprintd command-line operations](https://manpages.debian.org/testing/fprintd/fprintd-enroll.1.en.html)

This document records the target architecture, **not an installed or working libfprint driver**. Physical 5955 operation remains limited to the current experimental diagnostic tools until an actual driver is built and tested.
