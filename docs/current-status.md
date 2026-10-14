# FocalTech 2808:5955 — current project status

**Updated: 14 October 2026.** This page is the current snapshot of the 2808:5955 project. Older dated research documents deliberately retain their original hypotheses and incomplete milestones; read them as experimental history rather than current instructions.

## Goal and architecture

The goal is a **fully open-source Linux fingerprint driver**, initially for USB VID:PID `2808:5955`, with a device-profile/transport design that can eventually support other FocalTech readers where their hardware and protocol permit (including possible SPI variants).

Five areas have different maturity levels:

| Area | Current evidence | Limitation |
| --- | --- | --- |
| USB protocol and capture | Real 2808:5955 contact/release, handshake, image reads and 64×80 processed frames work on Nobara | Experimental bounded helper; not a production driver |
| Proprietary match-on-host (MOH) compatibility bridge | FocalTech Windows matching DLL executes under Linux in an isolated, USB-free bubblewrap process | Development reference with incomplete Windows API semantics; **not open source** |
| Offline enrolment and matching | 12 successful enrolment updates, duplicate precheck and mock-storage commit; 4/4 held-out same-finger matches with matching polarity | Not a measured false-accept or false-reject rate; no true different-finger security control yet |
| Live experimental enrolment GUI | One full physical-sensor session completed with 12 usable impressions, 4 rejected, and a temporary in-memory template commit | Template wiped when session ends; **live verification has not yet been demonstrated** |
| Native C image/matching research | Independent image conversion and several components have synthetic tests | No validated, fully native open-source fingerprint matcher or libfprint driver yet |

**No working `fprintd`, PAM, KDE or system-login fingerprint integration exists yet.** Password login is unaffected.

## Known-good experimental sequence

The working *reference* approach, which must be kept intact during tidy-up:

1. Detect a **fresh touch** after a full finger release; the USB helper uses a bounded polling/capture budget.
2. Read a 10,240-byte raw frame; interpret as 5,120 little-endian 16-bit samples, converted to 64×80 8-bit using the current experimental contrast stretch.
3. **Invert the 8-bit image in memory** for Windows-like polarity and generally better vendor quality scores. The vendor engine also matched 4/4 held-out captures when *both* enrolment and verification used the original polarity; mixed polarities yielded 0/4 matches in the tested same-finger captures.
4. Call `SetEnrollmentParameters` (unknown subfactor), `QuerySampleHint` (12 samples), then `CreateEnrollment`/`AcceptSampleData`/`UpdateEnrollment` for new impressions. The 12th valid `UpdateEnrollment` returned `S_OK`. **Do not use the independent `GetEnrollmentStatus` result to override that completion in this tested workflow.**
5. Before `CommitEnrollment`, call `CheckForDuplicate`; the mock empty-database storage adapter implements `QueryByContent`. Commit to **temporary mock in-memory storage**. The temporary template is wiped at the end of the isolated session.
6. For held-out offline verification, `VerifyFeatureSet` returned `S_OK` on 4/4 same-finger captures with matched polarity. `0x80098005` is `WINBIO_E_NO_MATCH` (seen in the polarity-mismatch control). A genuine **different-finger** control is still required.

This sequence is **not** an instruction to store templates persistently or enable system authentication.

## Current entry points (feature branch)

For the complete, categorised inventory of all 58 tools without moving or deleting them, see the [tool and test index](tool-index.md). For a concise list of open milestones, use the [roadmap](roadmap.md). The original long-form [README](archive/readme-research-log-2026-10-14.md) and [roadmap](archive/roadmap-research-log-2026-10-14.md) remain archived for historical reproducibility.


| Purpose | Entry point | Type |
| --- | --- | --- |
| Experimental live enrolment | `tools/interactive_enroll_gui.py` | GUI with bounded USB helper and isolated engine |
| Fresh-touch USB acquisition | `tools/auto_contact_capture.py` | Privileged bounded helper; used by GUI |
| Isolated live GUI engine runner | `tools/test_moh_isolated_interactive_enroll.sh` | Builds and runs isolated MOH process |
| Reproduce offline enrol/commit/verification | `tools/replay_moh_enrollment.py` | Reads existing **local private** PGMs; no USB |
| Offline sandbox runner | `tools/test_moh_isolated_pgm_enroll_batch.sh` | Isolated test-only harness |
| Native research regression suite | `make -C native test` | Synthetic data; no USB/DLL |
| Other USB/protocol diagnostics | `tools/firmware_probe.py`, `tools/finger_status_probe.py`, `tools/image_capture_probe.py`, etc. | Historical tools; often require explicit `--send` |
| Windows evidence and reverse engineering | `docs/` and `tools/windows_*.ps1` | Read-only reference/research |

All code for the experimental MOH integration currently lives on **`feature/ft5955-moh-engine-bridge`**, not yet on default `main`.

### Safest regression test

```bash
make -C native test
python3 -m unittest discover -s tests -p 'test_*.py'
```

These run synthetic/isolated unit tests without automatically using the USB sensor or the proprietary driver. The Python test suite may require the project dependencies. They **do not** exercise the live vendor engine or prove live enrolment.

### Launch the live enrolment GUI (experimental, explicit USB opt-in)

From your existing, correctly configured feature-branch checkout:

```bash
sudo -v
python3 tools/interactive_enroll_gui.py --archive /path/to/7_Fingerprint-module.zip --send
```

Run the GUI as a **normal user**, not root; the USB helper alone uses `sudo -n`. Lift and press between captures. The helper is bounded to eight fresh touches per run; the GUI has a Continue button for the next bounded batch. The engine sandbox has **no USB or network access** and no persistent biometric storage.

## Data protection

- Never commit or upload real fingerprint raw frames, PGMs, PNG previews, Windows BIRs, matching templates, USB payload captures, user-identifiable metadata or proprietary DLL/archive files.
- Keep sensitive data under ignored `local-data/`; it must remain on the owner's computer. The ignore rules also cover relevant biometric file extensions globally as a safety net.
- Public regression tests should use explicitly synthetic examples.
- Do not enable `fprintd`, modify PAM or change KDE unlock/login configuration based on these experiments.

## Cleanup policy and future milestones

1. **Preserve** the working GUI, capture helper, isolated MOH engine, replay tools and regression tests without renaming paths or imports.
2. Keep old evidence and superseded native prototypes discoverable; identify them as historical rather than deleting them during early cleanup.
3. Treat the Windows DLL bridge as a reference-only stage while independently developing native, freely distributable image processing, feature extraction and matching.
4. Validate **live same-finger verification**, then **real different-finger rejection**, repeated across sessions, before introducing protected persistent template storage.
5. When security and reliability are proven, add a proper `libfprint` integration and test `fprintd` before any PAM/KDE authentication changes.
6. Only reorganise the many scripts after a dependency/import audit and a saved, passing baseline; then consider advancing the experimental branch toward `main`.

This page supersedes stale **status summaries**, not the dated technical findings.
