# FT5955 independent build AND private USB Claim: PASS (17 October 2026)

## Scope and actual result

**Evidence:** terminal output supplied by the user on Nobara, after a first private Claim-only attempt failed due to ordinary USB node access permissions. The command was:

```bash
python3 "$HOME/Projects/ft5955-independent-build-check/tools/verify_ft5955_clean_clone.py" --claim-only
```

This was performed from a **separately cloned copy of this GitHub branch**, not the original dirty `~/Projects/libfprint-ft5955` development checkout. The wrapper:

1. Verified the saved working-driver manifest and both historical Git patch SHA-256 digests.
2. Independently fetched the upstream libfprint release `v1.94.100` to disposable `/tmp` space, verified exact commit `80a4b5ec612892c5c056c48dddaa561452cf37ec`, and applied the three reviewed C/Meson patches.
3. Reconstructed the exact saved main FocalTech driver and the remaining driver/header sources, configured **27 Meson targets** for `focaltech_5955`, and compiled **Ninja 109/109** steps.
4. Used a separate, temporary private D-Bus, private PolicyKit helper, and private `fprintd` process, and verified that process **loaded the exact newly compiled libfprint shared object**, not the installed system library.
5. Discovered one private fingerprint device, **Claimed** the actual USB `2808:5955` reader, and **Released** it successfully.
6. Explicitly **did not request** `EnrollStart`, `VerifyStart` or biometric image/template capture; removed temporary private test state and built sources; left the live libfprint development checkout, system `fprintd`, PAM and KDE login unchanged.

Decisive observed output:

```text
[109/109] Linking target tests/test-fpi-device
PASS: CLEAN upstream clone + 3 GitHub patches built independently
PASS: private fprintd loaded the exact GitHub rebuilt libfprint.
PASS: discovered one private device: /net/reactivated/Fprint/Device/0
PASS: Claim succeeded using rebuilt GitHub library.
PASS: Release succeeded.
PASS: NO EnrollStart, VerifyStart or biometric capture requested.
PRIVATE BUS TEST PolicyKit: action=net.reactivated.fprint.device.verify decision=ALLOW
PASS: GitHub rebuilt driver: Discover -> Claim -> Release.
PASS: fresh-clone driver Discover/Claim/Release verified
PASS: disposable source and build removed; live driver, system fprintd, PAM unchanged.
```

**Conclusion:** the FocalTech device can be compiled from independent public upstream + this project's GitHub sources, and the resulting private `fprintd` process can actually open and close the real sensor on this Nobara machine. This closes the clean-source provenance/rebuild and basic USB Claim/Release milestones; **does not** validate production authentication, fully native matching, complete error recovery, repeatability or biometric security.

## USB node permissions (resolved for this one test)

The first `--claim-only` run compiled successfully and loaded the correct library, but Claim failed at `/dev/bus/usb/003/003` with `errno=13` / libusb `Access denied (insufficient permissions) [-3]`. Private PolicyKit had already decided **ALLOW**, showing that the block was a separate kernel/device-node permissions issue.

The user retried after setting a **temporary, per-user read/write ACL** on that exact USB node via:

```bash
sudo setfacl -m "u:$(id -un):rw" /dev/bus/usb/003/003
```

The subsequent clean-build private Claim and Release both passed. A device-node ACL granted manually is **not installed by the build script** and is **not automatically removed by private-fprintd cleanup**; it ordinarily disappears when that `/dev/bus/usb` node is removed and recreated. This is *not* a permanent udev rule and is *not* a tested system-wide USB permissions solution. Device bus/device numbers can change after re-enumeration; never blindly reuse the numeric path.

## Next phase: source-only security and reliability review

Prioritise these questions before any system `fprintd`/KDE login changes:

- **Cancellation and crash recovery:** `ft5955_native_action.c` worker subprocess lifetime, D-Bus disconnection/timeout, queued main-thread progress vs operation completion, and recovery after user cancel or device unplug.
- **USB protocol and safety:** `focaltech_5955.c` descriptor/handshake validation, release on failure, timeout and short-packet handling; `ft5955_native_capture.c` bounds, fresh lift/press, cancellation and image framing. Prefer synthetic/offline tests of malformed responses first.
- **Template handling and authentication boundary:** `ft5955_print_codec.c` uses **unkeyed SHA-256**, which detects accidental corruption but **does not authenticate a template against malicious replacement**; `ft5955_fpi_print_bridge.c` stores the vendor template as raw `FpPrint` bytes. Review confidentiality, database ownership/permissions and process memory lifecycle before any persistent storage. Existing experimental proprietary MOH gateway is still **not** a native matching implementation; audit sandbox policy and process isolation separately.
- **False accept and false reject control:** preserve the distinction between a retry, a genuine `NO_MATCH`, and a genuine `MATCH`. Prior individual private-fprintd tests had genuine false rejections; a second real press is an accepted usability tolerance but must not be implemented as a bypass. Existing limited different-finger controls do not constitute quantitative false-accept-rate validation.

No new physical fingerprint enrolments requested. The earlier RAM-backed private enrol/verify demonstrations remain **separate evidence** from today's rebuilt Claim-only hardware PASS.

## Test boundaries

No binary has been installed into the system authentication stack. Do **not** modify PAM or enable KDE fingerprint login in this stage. The previously skipped Meson driver/introspection tests remain skipped; Ninja build success does not represent full test-suite PASS. Neither successful private PolicyKit authorisation nor the temporary ACL demonstrates correct production device permission policy.
