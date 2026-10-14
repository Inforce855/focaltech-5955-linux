# FocalTech 2808:5955 — tool and test index

**Inventory reviewed: 14 October 2026** on `feature/ft5955-moh-engine-bridge`. All 61 files under `tools/` are indexed below; **no tool has been deleted, moved or renamed**. The distinction is between current working *experimental* code and exploratory/historical diagnostic tools, not between safe and unsafe binaries.

**Begin with [current project status](current-status.md) or [the root README](../README.md).** Current hardware success is experimental enrolment only; live post-enrolment verification and `libfprint`/PAM login remain unfinished.

## Entrypoint and privacy rules

- Run `tools/interactive_enroll_gui.py` as the **normal desktop user**, not as root. The GUI invokes `auto_contact_capture.py` via a scoped `sudo -n` helper. Use explicit `--send` only when you intend physical USB access.
- Isolated engine runners require a **privately owned matching DLL/archive**, extract it into disposable local storage and rely on opt-in flags. The production driver must eventually eliminate this dependency.
- Scripts that consume raw/PGM/BIR image data are **local private diagnostics**. Never upload or commit their input/output images or fingerprint templates.
- A tool being listed here does **not** guarantee that its command-line documentation still reflects the latest hardware understanding; historical utilities may deliberately describe earlier assumptions.
- Keep filenames and import paths intact until dependency tests and integration coverage justify a move.

## Current end-to-end operator workflow

*Active experimental workflow — **keep paths unchanged***

| File | Purpose |
| --- | --- |
| [`interactive_enroll_gui.py`](../tools/interactive_enroll_gui.py) | Tk enrolment GUI; communicates with a short-lived USB helper and isolated MOH process. |
| [`live_finger_identify.py`](../tools/live_finger_identify.py) | **NEW, UNVALIDATED on hardware:** terminal test: enrol two numbered fingers in RAM and identify a fresh touch. |
| [`auto_contact_capture.py`](../tools/auto_contact_capture.py) | Privileged bounded fresh-contact sensor helper; used by GUIs. |
| [`live_contact_viewer.py`](../tools/live_contact_viewer.py) | Private in-memory fingerprint image and zero-map viewer. |
| [`replay_moh_enrollment.py`](../tools/replay_moh_enrollment.py) | Replays existing private PGM images through the isolated Windows matcher; no USB. |
| [`capture_enroll_raw.py`](../tools/capture_enroll_raw.py) | Saves bounded private raw touch captures locally, for diagnostics. |
| [`convert_enroll_raw_to_pgm.py`](../tools/convert_enroll_raw_to_pgm.py) | Converts private raw frames to 64×80 PGM images for offline replay. |

## USB protocol and hardware diagnostics

*Hardware experiments; inspect `--help` and require explicit opt-in for any USB requests*

| File | Purpose |
| --- | --- |
| [`usb_probe.py`](../tools/usb_probe.py) | Device descriptor inspection and optional bulk IN listener. |
| [`firmware_probe.py`](../tools/firmware_probe.py) | Bounded firmware-information command. |
| [`finger_status_probe.py`](../tools/finger_status_probe.py) | Single finger-contact status request. |
| [`scan_handshake_probe.py`](../tools/scan_handshake_probe.py) | One-shot scan-handshake probe. |
| [`scan_ready_probe.py`](../tools/scan_ready_probe.py) | One-shot readiness-register probe. |
| [`image_geometry_probe.py`](../tools/image_geometry_probe.py) | Single width/height metadata query. |
| [`scan_preflight_capture.py`](../tools/scan_preflight_capture.py) | Audited handshake/status/ready/image preflight sequence. |
| [`image_capture_probe.py`](../tools/image_capture_probe.py) | Single or four-shot image-capture experiment. |
| [`image_transfer.py`](../tools/image_transfer.py) | Library code for bounded image transfer parsing (not a standalone sensor command). |
| [`protocol_codec.py`](../tools/protocol_codec.py) | Wire framing and response codec shared by probes. |

## Offline image and algorithm investigations

*Historical/ongoing research; not production identity decisions*

| File | Purpose |
| --- | --- |
| [`raw_to_png.py`](../tools/raw_to_png.py) | Private image conversion and display helpers. |
| [`raw_decode_preview.py`](../tools/raw_decode_preview.py) | Private image interpretation comparisons. |
| [`raw_sample_diagnostics.py`](../tools/raw_sample_diagnostics.py) | Aggregate 16-bit raw statistics. |
| [`row_boundary_probe.py`](../tools/row_boundary_probe.py) | Sensor image row/layout diagnostics. |
| [`fingerprint_compare.py`](../tools/fingerprint_compare.py) | Exploratory correlation of A/B samples; not authentication. |
| [`cross_session_eval.py`](../tools/cross_session_eval.py) | Exploratory cross-session image comparison. |
| [`real_capture_eval.py`](../tools/real_capture_eval.py) | Native converter evaluation on private images. |
| [`sift_compare.py`](../tools/sift_compare.py) | Offline OpenCV feature-matching experiment; not authentication. |

## Windows MOH compatibility analysis

*Static and offline compatibility research; many reports are historical baselines*

| File | Purpose |
| --- | --- |
| [`audit_moh_engine_features.py`](../tools/audit_moh_engine_features.py) | Static investigation of vendor matching-engine features. |
| [`compare_windows_bir.py`](../tools/compare_windows_bir.py) | Compares Windows BIR layouts against synthetic structures without uploading samples. |
| [`inspect_windows_bir.py`](../tools/inspect_windows_bir.py) | Private Windows biometric record format inspection. |
| [`moh_attach_disassemble.py`](../tools/moh_attach_disassemble.py) | Static attach-path disassembly helper. |
| [`moh_attach_static_audit.py`](../tools/moh_attach_static_audit.py) | Static attach-path compatibility audit. |
| [`moh_callback_abi_audit.py`](../tools/moh_callback_abi_audit.py) | Windows callback ABI analysis. |
| [`moh_engine_preflight.py`](../tools/moh_engine_preflight.py) | Checks a privately supplied vendor DLL and loader import coverage. |
| [`moh_pe_guard_check.c`](../tools/moh_pe_guard_check.c) | PE loader bounds/guard research helper. |
| [`moh_pe_guard_probe.py`](../tools/moh_pe_guard_probe.py) | Offline PE guard checks. |
| [`moh_teb_audit.py`](../tools/moh_teb_audit.py) | Thread environment block compatibility audit. |
| [`moh_teb_context.py`](../tools/moh_teb_context.py) | TEB inspection/support functions. |
| [`moh_tls_preflight.py`](../tools/moh_tls_preflight.py) | TLS callback/static safety preflight. |

## Isolated engine runners, fixtures and builds

*Internal development/test entry points — **not** standalone login tools*

| File | Purpose |
| --- | --- |
| [`build_moh_engine_smoke.sh`](../tools/build_moh_engine_smoke.sh) | Build-only smoke test for experimental compatibility engine. |
| [`moh_engine_attach_smoke.c`](../tools/moh_engine_attach_smoke.c) | Attach-path C probe fixture. |
| [`moh_engine_interactive_enroll.c`](../tools/moh_engine_interactive_enroll.c) | Persistent in-memory enrolment engine used by the GUI. |
| [`moh_engine_live_identify.c`](../tools/moh_engine_live_identify.c) | Bounded two-template C harness (runs only inside temporary isolated process). |
| [`moh_engine_interface_smoke.c`](../tools/moh_engine_interface_smoke.c) | Vendor WinBio interface C fixture. |
| [`moh_engine_pgm_accept.c`](../tools/moh_engine_pgm_accept.c) | Single-PGM offline sample acceptance fixture. |
| [`moh_engine_pgm_enroll.c`](../tools/moh_engine_pgm_enroll.c) | Single-sequence PGM enrolment fixture. |
| [`moh_engine_pgm_enroll_batch.c`](../tools/moh_engine_pgm_enroll_batch.c) | 12+4 enrolment, mock commit and verification fixture. |
| [`moh_engine_pgm_enroll_repeat.c`](../tools/moh_engine_pgm_enroll_repeat.c) | Repeated PGM enrolment experiment. |
| [`moh_engine_synthetic_accept.c`](../tools/moh_engine_synthetic_accept.c) | Synthetic vendor engine acceptance fixture. |
| [`test_moh_isolated_attach.sh`](../tools/test_moh_isolated_attach.sh) | Sandboxed attach-path runner. |
| [`test_moh_isolated_interactive_enroll.sh`](../tools/test_moh_isolated_interactive_enroll.sh) | Sandboxed live-GUI engine runner. |
| [`test_moh_isolated_live_identify.sh`](../tools/test_moh_isolated_live_identify.sh) | Sandboxed live-identification runner, based on the known capture/enrol isolation recipe. |
| [`test_moh_isolated_pgm_accept.sh`](../tools/test_moh_isolated_pgm_accept.sh) | Sandboxed PGM sample acceptance runner. |
| [`test_moh_isolated_pgm_enroll.sh`](../tools/test_moh_isolated_pgm_enroll.sh) | Sandboxed PGM enrolment runner. |
| [`test_moh_isolated_pgm_enroll_batch.sh`](../tools/test_moh_isolated_pgm_enroll_batch.sh) | Sandboxed 12+4 offline verification runner. |
| [`test_moh_isolated_pgm_enroll_repeat.sh`](../tools/test_moh_isolated_pgm_enroll_repeat.sh) | Sandboxed repeated enrolment runner. |
| [`test_moh_isolated_query.sh`](../tools/test_moh_isolated_query.sh) | Sandboxed engine query runner. |
| [`test_moh_isolated_synthetic_accept.sh`](../tools/test_moh_isolated_synthetic_accept.sh) | Sandboxed synthetic accept runner. |
| [`test_moh_native_compat.sh`](../tools/test_moh_native_compat.sh) | Native shim compatibility checks. |

## Windows VM observations and WinBio probes

*Reference-only tools; not needed to run the Linux GUI*

| File | Purpose |
| --- | --- |
| [`windows_vm_usbmon_probe.py`](../tools/windows_vm_usbmon_probe.py) | USB command/metadata monitoring with biometric redaction. |
| [`windows_winbio_async_probe.ps1`](../tools/windows_winbio_async_probe.ps1) | Windows WinBio asynchronous capture experiment. |
| [`windows_winbio_capture.ps1`](../tools/windows_winbio_capture.ps1) | Windows WinBio capture and BIR reference experiment. |
| [`windows_winbio_sample_probe.ps1`](../tools/windows_winbio_sample_probe.ps1) | Windows API capture-sequence experiment. |

## Temporary, labelled two-finger identification test (UNVALIDATED)

This CLI keeps both templates only inside a disposable sandbox process. It uses the same bounded sensor helper as the existing GUI, and deliberately does **not** save enrolments for later sessions.

```bash
# From the feature-branch checkout as a normal user
sudo -v
python3 tools/live_finger_identify.py \
  --archive /path/to/7_Fingerprint-module.zip --send
```

Follow prompts for **Finger 1**, **Finger 2**, then fresh identification touches. Each finger needs 12 accepted enrolment impressions; up to eight fresh touches are captured in each bounded helper session. Identification returns Finger 1, Finger 2, NONE, REJECTED or AMBIGUOUS, and engine errors abort the test rather than being interpreted as matches.

This is a **new experimental path** and may reveal engine callback/state issues when enrolling the second template. It has not been exercised on real hardware yet. Nothing installs in Linux login, and quitting wipes both temporary templates.

## Regression coverage

- **`tests/`** contains 48 source files covering Python code, protocol parsing, engine shims and safety gates. These files have not been renamed. Individual tests and their assumptions are documented in source.
- **`native/`** contains open-source image-processing research and C test programs. See [native README](../native/README.md) and [phased roadmap](roadmap.md).

```bash
# From repository root: synthetic/local tests; no new USB capture
make -C native test
python3 -m unittest discover -s tests -p 'test_*.py'
```

The offline vendor-engine test is separate because it needs the proprietary Windows DLL and private PGM input; use the `replay_moh_enrollment.py` interface described in [current-status.md](current-status.md).

## Before deleting or moving anything

1. Save a passing baseline from the actual Nobara checkout and verify ignored biometric files remain untracked.
2. Check all direct Python imports, shell references, C compile commands, test fixtures, documentation paths and any local desktop launchers.
3. Mark experiments as superseded only when the supported alternative and regression coverage are proven. Preserve evidence in Git history and research notes.
4. Move one group at a time with matching path/import updates; **never** reshuffle the isolated engine and GUI in the middle of a successful enrolment/verification milestone.

The original research-heavy README and roadmap are preserved in [docs/archive/](archive/).
