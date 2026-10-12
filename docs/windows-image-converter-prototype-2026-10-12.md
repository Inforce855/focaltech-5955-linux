# Offline 5955 Windows-image conversion prototype (12 October 2026)

We have stopped testing Windows Hello capture APIs. Their synchronous sample request hung, and the async-session attempt failed before capture with `0x8007000E`. The working VirtualBox login and `usbmon` trace remain our ground truth: the device returned `0x07 = 0` (conditional AES stage disabled) and one 10,246-byte framed sensor image was sufficient for authentication.

**This document adds a separate, synthetic-tested C11 prototype reconstructing the complete general 64×80 image converter from read-only instructions in the matching Windows MOH driver `FtWbioDriverUmdfV3.dll` (SHA256 `b2dd3b0a5c79c9a9bc628ccbfdbd20b83e63799d9d310ae513c378c7af1b958e`).**

- `native/ft5955_windows_spatial.c`: previously implemented 64×80 edge repair and four-neighbour anomaly correction at `0x180006184`.
- `native/ft5955_windows_converter.{h,c}`: additional processing reconstructed from `0x180005C78`: 16-bit negate and signed min-subtraction; 256-bin double-precision histogram indexing; three 256-bin float radius-2 smoothing passes; two additional 250-bin passes; an adaptive 5-bin-window cutoff search; and final truncated/clamped 8-bit scaling.
- `native/test_ft5955_windows_converter.c`: synthetic gradient, zero-image, negative-value, border and format-guard tests; tested with `-Wall -Wextra -Werror` and ASan/UBSan in the analysis environment.
- `native/ft5955_windows_converter_probe.c`: optional local CLI for **private existing** 10,240-byte unframed little-endian raw captures. By default prints aggregate stats **without saving an image**. With an explicit `local-data/*.pgm` output it writes a private, 0600-permission grayscale PGM for local viewing only.

## Run on Nobara — without USB, sudo or Windows

In the existing repository after pulling `main`:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror -I native \
  native/ft5955_windows_spatial.c \
  native/ft5955_windows_converter.c \
  native/test_ft5955_windows_converter.c -lm -o /tmp/ft5955_windows_converter_test
/tmp/ft5955_windows_converter_test

cc -std=c11 -O2 -Wall -Wextra -Werror -I native \
  native/ft5955_windows_spatial.c \
  native/ft5955_windows_converter.c \
  native/ft5955_windows_converter_probe.c -lm -o /tmp/ft5955_windows_converter_probe
```

If a private saved 10,240-byte raw file is at `local-data/fingerprint_12-10-2026_01-56-41.raw`, report aggregate conversion stats without any image:

```bash
/tmp/ft5955_windows_converter_probe local-data/fingerprint_12-10-2026_01-56-41.raw
```

Optional, for an **offline local-only visual** of the same already-saved fingerprint:

```bash
/tmp/ft5955_windows_converter_probe \
  local-data/fingerprint_12-10-2026_01-56-41.raw \
  local-data/ft5955_windows_candidate.pgm
```

View PGM only on your own system (e.g. Gwenview). The CLI will refuse to overwrite an existing preview or save anywhere other than directly under the gitignored `local-data/`. Do not share real fingerprint images, upload PNGs to ChatGPT, or commit biometrics to GitHub.

## What the prototype proves — and what it does not

**Proven by static reconstruction and synthetic testing:** the C code follows the observed general conversion stages, and can convert an isolated synthetic gradient to an 8-bit 64×80 PGM. It has no hardware operations or installed-system effects.

**Not proven:** bit-exact agreement with actual Windows DLL execution, correct handling of every sensor raw range, orientation/polarity in a reader-specific post-step, or successful minutiae extraction. We have NOT compared a common real sensor buffer through both converter implementations. The Windows engine's template pipeline has separate tuning and may be incompatible with generic NBIS even after this conversion. Do not replace our functioning capture/bridge or modify fprintd/PAM yet.

## Another relevant interoperable FocalTech implementation

[OMGrant/ft9201-libfprint](https://github.com/OMGrant/ft9201-libfprint), especially [PORTING.md](https://github.com/OMGrant/ft9201-libfprint/blob/master/PORTING.md), is a working **different hardware model** (`2808:93a9`) that uses a small Linux-host PE loader to call FocalTech's own `ftWbioEngineAdapter.dll`, rather than libfprint's NBIS. Its engine expects a **64×80 BIR** even though its sensor outputs 96×96 frames; that geometry is notable but **not proof** of compatibility with the `2808:5955` engine.

Our actual **MOH** `ftWbioEngineAdapter.dll` is PE32+ x86-64 (SHA256 `a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c`). Read-only import inspection shows `KERNEL32.dll`, `ADVAPI32.dll` and `SETUPAPI.dll`; `WbioQueryEngineInterface` is exported. This means it could be a candidate for **separate, private, offline engine compatibility research**, but the FT9201 loader needs at least additional shims and ABI verification. It must not simply be installed or wired into login.

**Next decision point:** inspect locally generated PGM for ridge visibility and run an **isolated** offline minutiae diagnostic on the candidate output. If NBIS still gives zero on sharp, non-saturated images, prioritize studying the vendor's own matcher and its BIR input, using OMGrant's documented open-source method as a reference, while keeping the original long-term fully native implementation goal clear.

## First physical-capture test — 12 October 2026

The owner compiled the standalone converter on Nobara; all synthetic tests passed. Without contacting the device or the Windows VM, they ran it on a previously acquired **private**, exactly 10,240-byte 16-bit unframed raw sensor capture. The program returned:

```text
Experimental 5955 Windows-conversion reconstruction; NOT DLL-validated.
Conversion: OK; image 64x80
Shifted 16-bit min/max: 0/2000
Cutoff bin: 166; scaling denominator: 1328; saturated pixels: 1221
No fingerprint image written to disk. Add private PGM path to opt in.
```

**Observation:** 1,221 of 5,120 pixels (approximately **23.8%**) reached the output's saturation threshold. This is substantial clipping, but without independent validation against the actual DLL's processed output it is **not proof of defective calibration or wrong reconstruction**. No biometric image or template is included here.

**Next controlled action:** use the existing `ft5955_windows_converter_probe` with an explicit output `local-data/ft5955_windows_candidate.pgm`; examine the 64×80 PGM **only locally**, comparing ridge clarity and spatial orientation with earlier private Linux previews. The CLI refuses to overwrite an existing file. Do not publish fingerprint screenshots, input raw data, or BIRs. If the image is saturated or unreadable, investigate stage-by-stage numeric equivalence rather than changing Windows Hello or USB commands.


## User visual assessment of first private PGM

After running the independent converter on the previously saved private capture, the operator viewed the local PGM **without sharing the image**. They report that the fingerprint ridges are **substantially darker and easier to see**, with **much less intermediate grey**: the image looks more black-and-white than the previous Linux normalizations.

They also describe a **triangular missing/contact-looking region in the top-left corner**, consistent with an area visible in earlier previews. Their front-mounted reader requires an awkward angled finger placement, so incomplete sensor contact is one **plausible**, unverified explanation. The image's 1,221 saturated-white pixels (23.8%) must **not** automatically be equated with the triangular missing region: pixel counts alone cannot establish spatial distribution or origin.

**Next minimal experiment:** lift finger completely (to trigger a fresh capture), position it centrally with as much sensor contact as feasible, take **one** new private 10,240-byte capture through the already-working Linux acquisition route, and run the same isolated converter. Compare local previews and aggregate saturation metrics. Do **not** change USB commands, Windows Hello or libfprint yet. No private fingerprint pixels, templates or raw buffers are added to Git.
