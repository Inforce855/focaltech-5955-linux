FocalTech 2808:5955: libfprint/NBIS resolution experiment
12-10-2026

The previous live bridge successfully transported eight real scans to an
isolated libfprint virtual-image device. NBIS found zero minutiae with
both native-v3 and contrast preprocessing at 10x enlargement (640x800).

The reference project's 10x factor is for SIFT/RANSAC, not NBIS. libfprint's
image-processing assumptions differ. This patch makes the live CLI default
to 2x (128x160) with linear interpolation and makes other scales optional.
It does not change USB logic, libfprint, fprintd, PAM, KDE or system drivers.
No claim of enrolment or fingerprint-verification reliability is made.

Install from existing focaltech-5955-linux working tree:
  tar -xzf ~/Downloads/focaltech-5955-libfprint-scale-fix.tar.gz
  .venv/bin/python -m unittest discover -s tests -p test_live_libfprint_bridge.py -v

Enrol terminal (new session; leave it running):
  bash tools/run_isolated_enroll.sh

Bridge terminal (existing code, new scale mode; use normal user):
  sudo -v
  .venv/bin/python tools/live_libfprint_bridge.py --scale 2 --processing contrast

Lift/re-touch with the selected physical finger. Compare NBIS messages in the
first terminal. If still no minutiae, do not collect additional sets yet:
image polarity, calibration and whether the source contains NBIS-detectable
ridge morphology need to be investigated. Try native-v3 at the SAME scale only
as a second controlled variant, not a simultaneous uncontrolled change.

A fresh live helper session is limited to eight real presses. No raw scans
or templates are saved by the bridge; upstream enroll may store biometrics
in private local-data/libfprint-live. Do not upload fingerprints or templates.
