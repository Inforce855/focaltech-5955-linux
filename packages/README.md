# FT5955 experimental test packages

This folder contains complete, stand-alone source archives for isolated development tests. No fingerprint images, enrolment templates, or proprietary FocalTech DLLs are included.

## Native validation v0.9.1

- `ft5955-native-validation-v0.9.1.tar.gz`: source-only, 10-check same-finger/different-finger repeatability diagnostic, builds against an already compiled **private** libfprint checkout on Nobara. It does not change the working driver or install system authentication.
- SHA-256: `857d445ee7dc01e11a1aa7cec3bb9cdeb4685e859e0f2784631110877fb1979f`.
- Extract into `~/Projects`, run `bash run_source_tests.sh` and `bash build_private_test.sh` in the extracted folder, then follow its README for an explicitly authorised live session.

The previous v0.9 check matched the enrolled finger once and correctly rejected two other fingers, but unexpectedly rejected the enrolled finger on its last attempt. v0.9.1 records each result; it does not mask false rejections or false matches. Do not enable fprintd/PAM with this experimental build.
