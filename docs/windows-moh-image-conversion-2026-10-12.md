# MOH FocalTech 2808:5955 — Windows image conversion disassembly

**Investigation: 12 October 2026.** Read-only disassembly of the owner's actual matching MOH driver. **Not** an operational Windows-based driver or a complete image converter. No Windows binary or biometric data is committed.

## Original binary and provenance

- Archive (private): `7_Fingerprint-module.zip`, directory `MOH/FocalTechFPSSOdriver25H2x64V5.10.66.6611_WHQL` (NOT the MOC/FT9365 package).
- `FtWbioDriverUmdfV3.dll`, PE32+ x86-64, 748,224 bytes; image base `0x180000000`.
- SHA256: `b2dd3b0a5c79c9a9bc628ccbfdbd20b83e63799d9d310ae513c378c7af1b958e`.
- Analyzed using **read-only** `llvm-objdump`; not run or patched. All addresses below are preferred image VAs.

## Verified GetImage call chain

At `0x180006B74`, `ff_sc_GetImage`:

1. `0x180006C36..6C3E`: reads dimensions from device object `+0x5A` (width), `+0x5B` (height), multiplies them.
2. `0x180006C62..6C81`: allocates `2 × width × height` raw bytes and invokes acquisition helper `0x18000793C`.
3. `0x180006CF0..6D1E`: **conditional preprocessing**. If device byte `+0x268 == 1`, calls `0x1800016A4` with raw input and globals near `0x180025000`/`0x180025010`. This path and its state initialization have NOT been reconstructed.
4. `0x180006D23..6D56`: special `152×40` images use `0x18000510C`; all others use general converter **`0x180005C78`**, passing image input, height, width and 8-bit output buffer.

**Important geometry finding:** The sensor reports 80×64 metadata, but the general converter's first helper explicitly uses a **64-column stride and 80 rows**. This strengthens the previous physical row-layout finding of **64×80** for this hardware; it does not mean the general helper works for arbitrary sensor dimensions.

## Newly traced correction helper: `0x180006184`

`0x180005C78` first calls this function at **`0x180005CA2`**, *before* the histogram conversion. It mutates the 16-bit raw samples in place:

| Address | Read-only disassembly finding |
| --- | --- |
| `0x1800061A0..61C7` | Clamp signed-negative 16-bit words to zero, across given sample count |
| `0x1800061C9..622E` | Edge-column repair, fixed 64-word stride: copy x2→x1→x0 and x61→x62→x63 in every row |
| `0x180006230..6284` | Edge-row repair: copy row 1→row 0, and row 78→row 79, fixed 64 words per row |
| `0x180006286..6374` | In-place four-neighbour impulse correction on x=2..61, y=2..77. If >=3 of left/right/top/bottom exceed center+50 **or** >=3 are less than max(center−50, 0), replace center with 16-bit-wrapped sum of those neighbours divided by four (right-shift 2). Order and 16-bit arithmetic matter. |

**Implementation:** See `native/ft5955_windows_spatial.c` and `.h`, and synthetic regression `native/test_ft5955_windows_spatial.c`. These files independently implement **only** the correction helper, not the full image conversion, and are not connected to libfprint, the USB bridge or authentication.

Synthetic test (no sudo/device access):

```bash
cc -std=c11 -Wall -Wextra -Werror -I native \
  native/ft5955_windows_spatial.c native/test_ft5955_windows_spatial.c \
  -o /tmp/ft5955_windows_spatial_test
/tmp/ft5955_windows_spatial_test
```

All current tests pass with the above standalone build. We have **not** compared this native function byte-for-byte against an executing proprietary DLL. Fixed geometry and sample-count guard are added safeguards.

## The remainder of the general converter `0x180005C78`

This is the **actual 5955 MOH Windows path**, not an assumed equivalent from another model:

| VA | Observed operation |
| --- | --- |
| `0x180005CB1..5CC4` | Negate each 16-bit word **in place** (`neg ax`, wraps as 16-bit) |
| `0x180005CC6..5CF1` | Find *signed 16-bit* minimum and subtract it in place, using 16-bit arithmetic |
| `0x180005CF3..5D24` | Find signed minimum and maximum after offset removal |
| `0x180005D24..5DAB` | Construct 256-bin histogram with `(sample - min) * 256 / (max - min + 1e-6)` |
| `0x180005DAD..5E1B` | Convert counts to floats, moving-average smoothing (helper `0x1800060A8`) **three passes**, radius 2 |
| `0x180005E20..5EDD` | Copy first 250 bins, moving-average smoothing **twice more**, radius 2 |
| `0x180005EE2..5FC6` | Determine adaptive cutoff, including bins 200–249 and several threshold tests |
| `0x180005FCA..602F` | Convert corrected image to 8-bit output, dividing by adaptive range and clipping above 255 |

Confirmed `.rdata` numeric constants: VA `0x18001AFF0` = **1e-6** (double), `0x18001AFF8` = **0.8** (double), `0x18001B000` = **75.0** (float), `0x18001B004` = **100.0** (float). These come from actual PE bytes.

`0x1800060A8` is a float moving-average smoother over `index ± radius`, with clipped boundaries, copying its temporary output back in place.

## Significance and unresolved items

- The existing native-v3 path **does not apply** the now-confirmed `0x180006184` pre-histogram spatial correction, and is therefore **not** a faithful complete port of this matching Windows converter.
- The user's live libfprint bridge works at the image-transfer level. But the NBIS detector reported **0 minutiae** for all 20 tested variants (two normalisers, five scales, both polarities). This doesn't prove the sensor is bad: image correction is incomplete, and FocalTech's proprietary extractor uses a different feature representation from standard NBIS.
- **Next investigation:** trace `0x18000138C`, `0x18000125C`, `0x180001120` (called by the conditional preprocessing wrapper `0x1800016A4`), and resolve the state at `+0x268`. Then implement the remaining histogram/cutoff stage as a separate experimental converter, with synthetic numerical tests before any real images or integration.
- Do **not** link/commit Windows libraries or real fingerprint data, send unverified USB commands, or change installed libfprint/fprintd/PAM.

### Reproduce disassembly locally (private copy only)

```bash
llvm-objdump -d --x86-asm-syntax=intel --start-address=0x180006184 --stop-address=0x180006397 FtWbioDriverUmdfV3.dll
llvm-objdump -d --x86-asm-syntax=intel --start-address=0x180005C78 --stop-address=0x1800060A5 FtWbioDriverUmdfV3.dll
llvm-objdump -d --x86-asm-syntax=intel --start-address=0x180006B74 --stop-address=0x180006D56 FtWbioDriverUmdfV3.dll
```

## Follow-up: conditional AES-like image decryption (12 October 2026)

A deeper trace substantially narrows the unresolved `0x1800016A4` stage; the branch is **not simply a tone-calibration routine**:

- `0x180004868` first clears the per-device byte at `+0x268`, then `0x18000486F` calls `0x180006E90`. That helper uses existing metadata read function `0x180007B8C` with **selector `0x07`, response length 1, destination `device + 0x268`**. So this is a device-reported flag, not a hard-coded assumption. **The flag's value on the physical 5955 has not been measured. Do not send this untested command casually.**
- `0x180006CF0..6D1E` invokes wrapper `0x1800016A4` **only if the returned flag equals 1**; the same gate appears at `0x18000C00E..C043` on a second image-processing path.
- `0x1800016A4` expands a 16-byte key through helper `0x18000138C` and, with the Windows caller's mode argument 0, invokes `0x180001120` on the image buffer. The opposite branch uses `0x18000125C`.
- The binary contains **the exact standard AES substitution tables**: `0x1800195E0` begins with the well-known AES forward S-box sequence `63 7c 77 7b f2 6b 6f c5`; `0x1800196E0` begins with the inverse S-box sequence `52 09 6a d5 30 36 a5 38`. Both are accessed by the respective transformation routines, which process 16-byte blocks with rounds, XOR state, and a 16-byte auxiliary parameter. This is strong direct evidence for an **AES-family block cipher** and a likely decryption operation when mode 0 is selected. Further control-flow inspection supports **AES-128-CBC-style chaining**: the inverse transform at `0x180001120` processes 16-byte blocks from the end, XORing a decoded block with the previous input ciphertext block (`0x18000121F..122B`) or the supplied auxiliary block for the first block (`0x18000120A..121B`); the forward transform `0x18000125C` processes blocks in the opposite direction, with an XOR before the forward substitution rounds (`0x1800012BF..12D4`). The key schedule at `0x18000138C` uses a 16-byte input and ten rounds. The exact DLL output has **not** been dynamically validated, and the physical sensor's encryption flag is still unknown.
- The caller supplies two 16-byte constants from its own data section for key/auxiliary state. **Actual key material is intentionally not recorded in this public research document.** The private DLL itself is not published.

**Consequences:** Our presently working USB reader performs no selector-07 query or conditional decryption. If the physical device reports flag 1, a missing decrypt stage could completely invalidate our image-conversion tests; if it reports 0, the branch is bypassed and is not the explanation for the zero-minutiae results. Previously visible apparent ridge structure suggests some meaningful spatial signal, but is not proof of either encryption mode. This distinction must be resolved *before* attributing the failure entirely to histogram normalisation.

The next non-hardware work is to document the exact `0x180001120` input/output and chaining logic and inspect the code that uses the flag. Do not modify USB protocol, disable encryption, patch the DLL, or publish real fingerprints/keys as part of this research.

## Resolved on working Windows VM — 12 October 2026

A **live Windows guest restart followed by successful fingerprint login** on this exact 2808:5955 sensor was observed with the host's redacting usbmon monitor. Its `0x80` selector `0x07` response was **validly framed and checksum verified as byte `00`**. This is now an observed device property in the tested Windows startup, resolving the earlier *unknown* status above.

Since `ff_sc_GetImage` invokes the optional AES-like wrapper only when `device+0x268 == 1`, the **conditional AES step is bypassed in this working configuration**. Do not implement it as a prerequisite for the current sensor's Linux capture. Focus on the general `0x180005C78` path, including spatial correction `0x180006184`, its histogram and adaptive cutoff, and eventually the vendor feature extractor. This does not prove all capture and enrollment modes behave identically.

Full redacted trace interpretation: [Windows VM USB observation](windows-vm-usb-observation-2026-10-12.md).
