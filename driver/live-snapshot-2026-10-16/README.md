# FT5955 live driver source snapshot — 16 October 2026

Captured from the experimental private checkout, not the old archive.
Source-preservation snapshot. **Rebuild-only PASS on Nobara, 16 October 2026:** reconstructed pinned libfprint 1.94.100, Meson configured FocalTech-only driver, and Ninja compiled all 109 build steps; no install, hardware scan, or enrolment. See [rebuild report](../../docs/rebuild-ft5955-without-enrolment.md). **17 October 2026 USB Claim-only hardware PASS**: the rebuilt binary was confirmed loaded by the private fprintd and successfully discovered, claimed and released the real reader, with no biometric capture or enrolment. Full matcher/runtime biometric testing of this rebuilt binary remains pending.

Base libfprint Git commit: c8e01dc26cedb2d97779a314a7260f1c33e02bfa

The patches directory preserves local changes to the tracked Meson
and main driver source relative to the commit above. All 13 active
driver/header source files are preserved in libfprint/drivers.
Obsolete backup copies, biometric data and vendor binaries excluded.

Gateway files: engine_gateway.py, template_runner.py, template_session.c

## SHA-256 file hashes

engine/engine_gateway.py: 3d109c63658d1159f5484a9569ecfbbb56e62383a7d133c9c9aed38264a61f2e
engine/template_runner.py: b2a9af482368a977e3047a9412b3b26aa4ce67a58135684665189dd5c96acf7b
engine/template_session.c: 964146a6fa6f08a21f9492bfacbc17eb4ea5bfc3dbd90ebbbe27d366f31b21da
libfprint/drivers/focaltech_5955.c: 40418e509506400a4118a35f76a0482ad614b855d285d88971e342b81ebad703
libfprint/drivers/ft5955_action_core.c: 2708fcc7de3f1768c9dc571d842eb9fa8575ce6f1628e587dedd703dda532113
libfprint/drivers/ft5955_action_core.h: 7664d6986d3efda52c6962c62f53a29d8862b71a28fbb1bf3d4697159119e344
libfprint/drivers/ft5955_fpi_action_bridge.c: 12b93c1f1ef2197e22a90278991a11df8214b7fe7030815b507c3d7ff7d60df6
libfprint/drivers/ft5955_fpi_action_bridge.h: 0f6be9453390a528ec107aa8a344d09fc0c6e82981aeb91775d94a536e840cca
libfprint/drivers/ft5955_fpi_print_bridge.c: 5773929a73a548eb9de535484ef0d38d084d60a07a90aa74379bdaee979e6956
libfprint/drivers/ft5955_fpi_print_bridge.h: b320a2ec288ac810f975727a23d69be6250949bfd16fb04ab11310d129ec2fda
libfprint/drivers/ft5955_native_action.c: 0f52c8de56f4ee524f1225bd0db559262505c21f906b4034def1e01d61ec94ab
libfprint/drivers/ft5955_native_action.h: 4c7098d939e792540d82320dd9bcf2eb5899dec9571cc8172d22b9541c5629ee
libfprint/drivers/ft5955_native_capture.c: 07715cc8b6831fd320e2dd04752772f66289a405d124657d9a601ed8c6dbe35b
libfprint/drivers/ft5955_native_capture.h: f8083fc61b00708ee653e3a150e50a89ddb266c42928792b805fb30592724745
libfprint/drivers/ft5955_print_codec.c: e8fd29fae365937c9af47045eca9c5a6e1cc2e80bc9854537d309acbd687b4e8
libfprint/drivers/ft5955_print_codec.h: 304e936de0d865d9dfa92599a3dedda649eb4d8907a3978465fe2621356f2d99
patches/local-libfprint-changes.patch: 78a4bebf2ac0c65151c3f1d17a72b48b499abcaec48f6775ff24ad37373367a7
