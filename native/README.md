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
into an ignored native/build/ directory and runs 47 component checks plus 8 byte-output golden vectors on entirely synthetic
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

## Integrated histogram-selected tone mapping (v2, still research-only)

The new `ft_focal_tone_v2.c` integrates the already tested three-pass
256-bin smoothing, two-pass 250-bin smoothing and **data-dependent cutoff
search** into a 5120-word signed-input-to-8-bit-output prototype. Unlike
the superseded v1 experiment, this no longer imposes a fixed 20% contrast
clip. The cutoff multiplies the observed 16-bit range and is divided by
250 before scaling each inverted pixel. Five synthetic tests cover both
cutoff branches, input integrity, flat frames and extreme signed words.

**Verified against native ELF instructions**: the `ft9362_histNormalize`
routine at Ubuntu ELF address `0x4f510` uses the cutoff to calculate a
pixel scaling denominator (`0x4f8db` to `0x4f953`); the conditional
contrast-range search is at `0x4f84f` to `0x4f8d6`.

**Not verified**: byte-for-byte output, native 5955 calibration, extreme
signed-value wrapping and proprietary library compatibility. The original
vendor code performs in-place 16-bit operations, while our safe independent
implementation deliberately avoids modifying input. We have **not executed**
any vendor binary; this stage was compared with static disassembly only.

This module is a standalone offline research prototype and does not replace
our known-working device USB path, existing image converter, or login stack.

## Native tone v3: corrected scaling denominator (static evidence)

The FT9362 Ubuntu 2025 ELF disassembly (function at address `0x4f510`)
includes an **extra `1e-6` in the final output-scaling denominator**
(`0x4f91f`), after integer truncation of the cutoff-adjusted range
(`0x4f8f1` through `0x4f90a`). It multiplies the adjusted pixel by
255, divides in double precision, converts by truncation and caps
values above 255. Our earlier experimental `v2` omitted the epsilon.

The independent `ft_focal_tone_v3.c` models that arithmetic for the
**nonnegative signed-16 sample domain previously observed on this reader**.
It fails closed with status `-2` on unsupported negative values instead
of guessing FocalTech's signed 16-bit wraparound behaviour. It performs
**no USB access**, does not load the proprietary ELF, and leaves the
existing converter and `v2` research implementation unchanged.

Six synthetic tests cover the specific epsilon boundary (a full-scale
gradient maps to 254 rather than 255), a nondefault histogram cutoff,
error handling, flat arrays, unsupported signed values, deterministic
output and no mutation. The tests pass with GCC and ASan/UBSan in the
analysis container.

**Important:** This is an arithmetic correction grounded in static
machine instructions, NOT a byte-for-byte comparison against actual
FocalTech library output. Exact vendor equivalence, image calibration,
and matching quality remain unverified; no fingerprint or authentication
decision can be based on this research component.

## First measured output parity against the actual vendor code (11 October 2026)

The original native Ubuntu 2025 proprietary Linux `ft9362_histNormalize` at ELF
address `0x4f510` was run **locally only in the analysis container**, not
on the user's Nobara system. It used eight **synthetic-only** 64×80 16-bit
input patterns, never a user's fingerprint or enrolled template.

Isolation: the original ELF was loaded under an unprivileged user/network
namespace with no USB device passed through. A private, deliberately inert
`libgusb.so.2` shim aborted on **any attempted USB API call**. Neither
the ELF nor its shim was copied to our public GitHub repository.

Our independent algorithm's mathematical output model was checked against
the **actual original function's 5120-byte outputs** for each vector.
The byte counts, FNV-1a 64-bit hashes and selected cutoff modes agreed in
**all eight cases**, including a high-tail/adjusted-cutoff example.

The source file `test_ft_vendor_golden.c` now stores **only synthetic
input-generation formulas and aggregate reference checksums**; running
`make -C native test` on Nobara invokes solely our compiled C and
does NOT load any vendor DLL/ELF, access the fingerprint reader or
modify system authentication. We deliberately checked broad ramp,
bimodal, sparse, pseudo-random, column-gradient and near-flat patterns.

**Limitation:** byte parity has been measured for eight synthetic inputs
against a related FT9362 Linux normalizer, **not** for 2808:5955 actual
sensor calibration and **not** for the Windows MOH engine or matcher.
Negative signed samples were not exercised by these golden vectors.
Successful tests do not establish safe authentication accuracy.
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

## Initial native 256-bit feature-packing study (independent C)

The 2025 Ubuntu FT9362 ELF includes an actual descriptor writer inside
`FtComputeDescriptors` (`0xde190`). Its DWARF-backed `ST_Feature` record is
44 bytes: 3 float32 coordinates/orientation followed by 8 uint32 words
of bit-packed descriptor data, starting at byte offset 12.

**Recovered specific descriptor branch:** at `0xdf320`–`0xdf511`, code
clears all eight descriptor words, then compares two sets of 8×8
orientation histogram values against their eight-cell per-orientation
means (`× 0.125f`). It stores these results in the first 128 bits.
It then compares neighbouring cells with a threshold multiplier
`1.05f`, including wrap-around between the last and first cells,
into the remaining 128 bits. Each comparison sets one corresponding bit
in one of eight 32-bit words. The constants were checked in original
ELF read-only `.rodata` at `0x193740` and `0x193744`.

The **independent, offline** `ft_descriptor_pack.c` implements this
particular *histogram-to-binary-bit* branch using synthetic arrays.
Five synthetic tests verify its 44-byte/offset ABI, bit order, averaged
comparisons, circular-neighbour comparisons and error handling.
The original library is not linked, loaded or executed by the test.

**Limits:** This is one observed FT9362 branch; the scale-space detector,
gradient histogram calculation, alternative feature modes, feature
ordering, template serialization and identity matcher are **not** yet
reconstructed or vendor-output-validated. Do not use any resulting
features for biometric verification or store real descriptor vectors.

## Upstream MFS orientation histogram study (512 values; experimental)

Read-only ELF disassembly of the Ubuntu 2025 FocalTech FT9362 native library
shows that **the intermediate descriptor histogram is bigger than the final
256-bit descriptor**. `FtComputeDescriptors` at `0xde190` allocates
`descrWidth * descrWidth * descrHistBins` float entries (`0xde233`–`0xde249`).
The sampled path loops a roughly 31×31 image patch (`-15..15`), computes
gradients via `FtMfsCalcGradMagOri`, rotates coordinates relative to the
keypoint orientation, wraps angle bins, and distributes the contributions
between neighbouring spatial and orientation bins. The orientation scale
constant at `0x19373c` is approximately **8/(2π)**, consistent with eight
angle bins. In the experimentally studied mode, the working histogram
shape is **8 spatial cells × 8 spatial cells × 8 orientation bins = 512
floating-point values**, before vendor-specific bit comparisons produce
the 256-bit `ST_Feature.bDescri[8]`.

The independent `native/ft_mfs_histogram.c` provides two offline research
functions: (1) a central-difference gradient field (right-minus-left and
above-minus-below), and (2) trilinear, Gaussian-weighted histogram votes
on a 31×31 patch around an explicitly supplied candidate keypoint.
Inputs are synthetic float arrays; no fingerprint capture or actual
feature detection is involved. Six C tests check gradient direction,
flatness, orientation-relative rotation, spatial localisation, image
edge bounds and invalid-input handling. Strict C11 + ASan/UBSan pass locally.

**Critical limitation:** the vendor uses a precomputed `GAUSS_WEIGHT_TAB`,
gradient-validity gating, configurable scale factors and multiple algorithm
modes. The C prototype uses our own Gaussian σ=8 and cell width=4,
which are **research approximations, not recovered exact vendor values**.
Furthermore, the earlier 128-float input to our bit-packing subroutine is
only an *isolated comparison branch*. We have **not** established the
correct vendor mapping from the full 512-bin histogram to that branch.
Do **not** feed these 512 values directly to the earlier bit packer or
claim end-to-end descriptor parity, enrollment or authentication accuracy.

The project test suite executes no vendor library and performs no USB I/O.

## First real-fingerprint practical test (PRIVATE, offline)

The synthetic tests establish that our native C algorithm builds and
follows known arithmetic. To find out what it actually does with the
**existing genuine 2808:5955 captures**, use the independent local-only
image converter and diagnostic at `tools/real_capture_eval.py`:

```bash
cd ~/Projects/focaltech-5955-linux
git pull --ff-only
make -C native build/ft5955_normalize_cli
python3 tools/real_capture_eval.py
```

The tool automatically selects the latest complete labelled A1/A2/B1/B2
capture set under the repository's **ignored** `local-data/` folder.
Alternatively supply four exact `.raw` paths in A1 A2 B1 B2 order.
All four captures must be regular 10240-byte little-endian sample files.
If a particular file contains signed-negative words or the image is flat,
the research converter rejects it with an explicit message instead
of pretending to know the correct vendor sensor-calibration mode.

It prints each of six pairwise correlations (A1/A2 and B1/B2 genuine
hypotheses plus four different-finger controls), then the strongest
cross-finger score and both margins. Translation window = ±6 pixels.
The numerical similarity backend is the *existing exploratory high-pass
correlation routine*, NOT FocalTech's still-unfinished 256-bit descriptor
matcher. Negative or overlapping margins are important diagnostic
failures to investigate, not something to hide or fix with a guessed threshold.

The script creates **two local/private grayscale PNG contact sheets**:

```text
local-data/native-real-test/<A1-capture-name>-v3-64x80-contact.png
local-data/native-real-test/<A1-capture-name>-v3-80x64-contact.png
```

Each contact sheet places **A1 top-left, A2 top-right, B1 bottom-left,
B2 bottom-right**. Open them locally in the file manager to inspect
ridge continuity and static sensor stripes. Do not upload, attach,
publish, or commit them: they contain real biometric imagery. Files are
written exclusively under ignored `local-data/`, with `0700` output
directory / `0600` file permissions and without overwriting existing files.
Use `--no-previews` to report only numerical results.

Everything runs on existing data without `sudo`, USB, live captures,
vendor DLL/ELF execution, network connections, firmware, driver
installation, `fprintd`, PAM or KDE login changes.

The C subprocess uses **our own** `ft5955_tone_v3_normalize` over stdin
to produce 5120 bytes of 8-bit pixel data on stdout; a standard-library
Python helper generates private PNGs and reuses the established scorer.
No external Python dependency or OpenCV is required.

**Meaningful goal:** determine whether the real processed images are
visually plausible and whether both same-finger pairs consistently outrank
every different-finger control. A successful run does **not** establish
a usable or secure biometric matcher. It is an offline engineering
evaluation of the image-processing stage on actual hardware captures.

After building the native binary, optional synthetic plumbing check:

```bash
python3 -m unittest discover -s tests -p test_real_capture_eval.py -v
```
