# FocalTech 5955 on Linux

Experimental Linux support for the **FocalTech USB fingerprint reader `2808:5955`**, developed and tested on Nobara Linux.

**Goal:** reliable enrolment and verification through standard `libfprint` / `fprintd`, eventually using a fully open-source matcher. **Not ready for system login or PAM.**

## Current status — 16 October 2026

| Component | Result |
| --- | --- |
| USB communication, finger detection and image capture | **Working on real hardware** |
| Isolated Windows MOH matcher bridge | **Experimental matching demonstrated**; proprietary reference dependency |
| Linux libfprint driver | **Experimental**; active uncommitted source in local development tree |
| Private `fprintd` enumeration and device Claim | **Passed on 14 October** |
| v0.9.6 enrol/verify test compilation | **Passed on 16 October** (no scan) |
| Actual `fprintd` enrolment and fresh verification | **Not yet tested** |
| KDE unlock, PAM login, persistent biometric database | **Not available** |

A limited two-finger experimental matching test succeeded previously; this **does not establish reliable or secure authentication**. The fully native open-source matcher remains unfinished.

[Detailed current status](docs/status-2026-10-16.md) · [Roadmap](docs/roadmap.md)

## Try the current private fprintd test

The v0.9.6 experiment is on **[`feature/ft5955-private-fprintd-v096`](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-private-fprintd-v096)**, in a [draft pull request](https://github.com/Inforce855/focaltech-5955-linux/pull/2). It requires the existing *local* experimental libfprint build and integration gateway; a fresh clone alone is **not yet sufficient**.

On the existing Nobara machine, after fetching the [test sources](experiments/private-fprintd/README.md) into the validation directory:

```bash
bash ~/Projects/ft5955-native-validation-v0.9.1/tests/ft5955_private_enroll_v096.sh --check
```

**Compile-only test: PASS.** The separate `--live` mode has **not yet been validated**, and must be run only after reviewing the [isolation and safety instructions](experiments/private-fprintd/README.md). It uses a private D-Bus instance and RAM-backed test storage, not system authentication.

## Project documentation

- [Current capabilities and limitations](docs/status-2026-10-16.md)
- [Next development milestones](docs/roadmap.md)
- [Private fprintd v0.9.6 test instructions](experiments/private-fprintd/README.md)
- [Hardware and USB protocol](docs/hardware.md)
- [Historical experimental README](docs/archive/readme-research-log-2026-10-16.md) and [detailed research roadmap](docs/archive/roadmap-research-log-2026-10-16.md)
- [MOH engine bridge development branch](https://github.com/Inforce855/focaltech-5955-linux/tree/feature/ft5955-moh-engine-bridge) — additional code and documentation developed before the v0.9.6 private-fprintd branch; not yet consolidated

## Security and contributions

**Do not** publish real fingerprint images, templates, capture payloads or proprietary Windows binaries. Do not modify system `fprintd`, PAM, KDE authentication or firmware while testing experimental code. Device-specific protocols must not be assumed to work on other FocalTech readers.

The repository contains code with differing origins/licences; **there is not yet a project-wide licence**. Review file-level notices before reuse or contributions.
