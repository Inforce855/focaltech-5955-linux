# Experimental native FocalTech 5955 image preparation (C11)

This is the **first independently written native image-processing component**.
It never communicates with USB, needs no external library, and is not used in
any login/authentication workflow. No vendor binary is built, loaded or run.

## Run the synthetic-only tests on Nobara

From the repository root:

```sh
make -C native test
```

Requires an ordinary C compiler (cc, e.g. GCC or Clang) and make. Compiles
into an ignored native/build/ directory and runs twenty-five tests on entirely synthetic
arrays. **No real fingerprint scans are needed and no system files are changed.**

## Histogram smoothing research

The second C11 module, `ft_histogram.c`, independently implements a five-bin
moving-average filter with clipped windows at histogram boundaries, supporting
one to three passes over 256 bins (or the 250-bin window also seen in the
disassembly). This matches the broad filter structure found in the unstripped
native FocalTech `fw9362_smooth_hist32f` function. **It is not yet integrated
into the main image converter** because downstream tone mapping and its
parameters are not fully understood. Five additional synthetic tests verify
constant-bin preservation, impulse response, edge windows, deterministic
output and invalid-input handling. The five original image tests remain.

## Histogram pipeline study

The third native C module, `ft_focal_histogram.c`, traces the **intermediate**
histogram calculations found in the native FT9362 library: negate signed
16-bit samples safely in 32-bit arithmetic, calculate a normalised 256-bin
histogram, smooth 256 bins in three passes, copy/smooth the first 250 bins
in two additional passes, then measure the [0,199] and [200,249] histogram
regions. The disassembly compares upper-bin mass against 80% of lower-bin mass
to choose a subsequent tone-mapping branch.

**This is not yet the vendor's full normalisation method**, not verified on
our `2808:5955` reader, and deliberately has no connection to the working
image converter, USB or authentication. It is an independent offline
implementation with five synthetic-only tests, including signed-value extremes,
flat-frame rejection, repeatability and invalid inputs.

## Tone-mapping branch research (experimental)

Following a closer read of the recovered FocalTech FT9362 Linux disassembly,
`ft_focal_tone.c` builds on the histogram research component to implement the
observed **200/250 vs 250/250 contrast-range selection**. The high-tail branch
uses a comparison between the upper 50 bins and 80% of the lower 200 bins;
this was initially modelled as a fixed 20% range clipping. **Closer
static disassembly showed this was too simplistic**: FocalTech actually
searches the smoothed histogram for a data-dependent cutoff. The branch is verified by static machine-code inspection, but
the overall routine remains a **research approximation**, not yet a byte-exact
FocalTech implementation or a validated pipeline for reader `2808:5955`. 

The original histogram-window scan, wraparound behaviour on extreme signed
values and all other unknown image-calibration details are **not** reproduced.
Five independent synthetic tests exercise both histogram distribution branches,
flat images, signed extremes, input immutability and bad arguments. The new
routine does **not** replace the existing 5955 preview conversion or USB code.
## Histogram cutoff selection: corrected interpretation

The fifth research component, `ft_focal_cutoff.c`, reconstructs the native
FT9362 histogram **window search** seen in subsequent disassembly. In the
normal branch it scans from bin 240 with a threshold of 75 and adds 30
to the selected cutoff bin. In the upper-tail branch it scans from bin
190 with a threshold proportional to lower/upper histogram mass.
It looks for a sustained low-mass region followed by a qualifying
five-bin window and falls back to bin 250 if no useful boundary is found.

**This corrects the earlier interpretation that the high-tail branch
always clips a fixed 20% of the contrast range.** The original
`ft_focal_tone.c` remains a *provisional, superseded approximation*;
it is deliberately left unchanged so previously validated tests still
run, while the new cutoff search is separately tested and studied.
Do **not** use either routine as an identity matcher, or as evidence
of a byte-exact reproduction of the proprietary transform. Further
work is needed to integrate the cutoff selection into image conversion
and to establish correct pixel mapping/calibration from static analysis.

The five new tests use synthetic histogram distributions and exercise
both branches, the no-boundary fallback, error checks and immutability.
No USB or FocalTech library execution occurs.

## Implementation status

* **Grounded by the 5955 capture measurements:** exactly 5120 16-bit
  little-endian words organised as 64 columns × 80 rows (working assumption).
* **Grounded by the Windows 5955 converter:** clamp negative signed 16-bit
  input measurements before intensity transforms. Our previously captured
  real samples had zero negative signed words.
* **Grounded by recovered native Linux ft9362_histNormalize:** an inversion
  and minimum-offset stage, followed by histogram-based intensity processing.
* **Our experimental approximation:** calculate an exact histogram over the
  inverted word values and contrast-stretch between 1%/99% quantiles. This is
  **not yet the vendor's actual smoothing and tonal mapping function**.
* **Safety:** immutable input, exact size checks, empty-image rejection,
  aggregate-only metrics, no files or USB, no external dependencies.

The output's orientation/polarity has not yet been validated for 2808:5955.
This is image-preparation research only; output may not be used for fingerprint
identity decisions, authentication, or assessing reliable recognition.

Further work: reconstruct the histogram smoothing and mapping of the actual
Linux binary, then derive the feature-extractor input contract from the
Windows 5955 WinBio engine. The native implementation must remain our own.
