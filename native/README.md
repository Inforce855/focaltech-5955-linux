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
into an ignored native/build/ directory and runs five tests on entirely synthetic
arrays. **No real fingerprint scans are needed and no system files are changed.**

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
