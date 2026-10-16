# FocalTech 2808:5955 — one-touch real NBIS diagnostic

**Purpose:** Find out whether libfprint's existing NBIS minutiae detector can
extract anything from the actual sensor data under controlled 8-bit conversion,
polarity and resize variants. This is an investigative tool, **not** a matcher
or replacement fingerprint driver.

This package adds new files only. It does not overwrite the live bridge,
installed libfprint, fprintd, PAM or USB firmware. It stores **no** images,
minutiae coordinates or templates. Only small statistical values and minutiae
counts are printed to the console.

## Install

From `~/Projects/focaltech-5955-linux`:

```sh
tar -xzf ~/Downloads/focaltech-nbis-one-touch.tar.gz
bash tools/build_nbis_diagnostic.sh
```

Requires the previously built isolated libfprint source and build paths,
plus the existing native v3 normalizer.

## Run (ONE real fresh finger touch)

```sh
cd ~/Projects/focaltech-5955-linux
sudo -v
.venv/bin/python tools/nbis_one_touch_diagnostic.py --live
```

No enrolment terminal is needed. Lift your finger and touch once when prompted.
The tool stops the USB helper after receiving the first real image.

Or, **without touching the sensor**, run the same diagnostic using one of your
previously captured private raw files:

```sh
.venv/bin/python tools/nbis_one_touch_diagnostic.py --raw local-data/your-existing-capture.raw
```

Please share only the **TEXT console output** if you want help interpreting it.
Do not upload raw fingerprints or screenshots containing ridge detail.

It tests both existing normalisers (contrast and native-v3), interpolation
at 1x, 2x, 3x, 4x and 10x, and normal/inverted pixel polarity, all against
**libfprint's own minutiae detection function**. A nonzero count only means
features were extracted from the image; it does not establish accurate
identification, matching or security.
