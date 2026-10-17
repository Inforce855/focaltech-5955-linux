# Documentation index

**Current status:** 17 October 2026. See the [project README](../README.md) for verified capabilities and security caveats, and the [next-session handoff](next-session-handoff.md) for the shortest path back into development.

## Current practical results and source of truth

| File | Purpose |
| --- | --- |
| [Next-session handoff](next-session-handoff.md) | What is finished, what remains, what **not** to retest |
| [Full KDE lab enrolment, verification and rollback](kde-short-lived-trial-2026-10-17.md) | User-observed system `fprintd` / KDE successful two-finger enrolment, `verify-match`, user-reported multi-tap reliability and tested removal |
| [Current roadmap](roadmap.md) | Complete checklist and engineering tasks, with older entries retained as dated evidence |
| [Driver source snapshot](../driver/live-snapshot-2026-10-16/README.md) | Authoritative, checksum-verified driver and MOH-gateway source; avoid edits without updating provenance |
| [Source consolidation](consolidation-2026-10-17.md) | Independent reconstruction from upstream libfprint and three pinned source patches |
| [Independent hardware/source build PASS](independent-hardware-pass-2026-10-17.md) | Pinned upstream clone, build, physical private Claim/Release |
| [System driver activation and rollback PASS](system-fprintd-install-rollback-pass-2026-10-17.md) | First **discovery-only** real system trial, followed by explicit rollback |
| [MOH broker and failed nested bwrap alternative](nonroot-moh-broker-prototype-2026-10-17.md) | Synthetic socket tests, root/non-root process separation, and consciously abandoned nested sandbox experiment |
| [Reversible system trial plan](reversible-system-trial-plan.md) | Narrow installation guard, packaging assumptions and rollback design |

## Research references

- **Core USB capture and data:** [hardware](hardware.md), [protocol](protocol-research.md), [USB frame format](usb-frame-format.md), [image acquisition](image-acquisition-research.md), [image format](image-format-investigation.md).
- **Matching research:** [fingerprint matching](fingerprint-matching-research.md), [native matcher strategy](moh-engine-native-matcher.md), [native C tools](../native/README.md), [FT9201 comparisons](ft9201-engine-porting.md), [MFS feature extractor](mfs-feature-extractor-dwarf.md).
- **Windows reference behavior and reverse engineering:** [real VM USB observation](windows-vm-usb-observation-2026-10-12.md), [Windows engine matching](windows-focaltech-engine-matching-2026-10-12.md), [spatial conversion](windows-moh-image-conversion-2026-10-12.md), [feature disassembly](windows-moh-feature-extraction-disassembly-2026-10-12.md), [image-conversion prototype](windows-image-converter-prototype-2026-10-12.md), [VM events](windows-event-log-identification-2026-10-12.md), [WinBio diagnostics](windows-winbio-sample-probe.md).
- **Legacy source/notes:** [archived README](archive/readme-research-log-2026-10-16.md), [archived roadmap](archive/roadmap-research-log-2026-10-16.md), [older versioned experiments](../research/source-history/README.md), [dated 16 October status](status-2026-10-16.md). These describe what was known *at their date*, not the current release state.
- **Early private-fprintd tests:** [private v0.9.6/v0.9.7 harness](../experiments/private-fprintd/README.md), [16/17 October source rebuild evidence](rebuild-ft5955-without-enrolment.md).

## Privacy, provenance and scope

The project must **never** distribute raw biometric samples, authentic fingerprint templates, the proprietary Windows DLL, credentials or private logs. The matching engine in the successful KDE laboratory trial is still proprietary and experimentally adapted. No production login/PAM authentication has been validated. The three source patches and dated snapshot are deliberately preserved; the historical branches and open research PRs are also retained, not bulk-deleted.
