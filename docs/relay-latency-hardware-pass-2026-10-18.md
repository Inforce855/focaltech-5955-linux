# FT5955 relay latency hardware test — 18 October 2026

The user's Nobara system activated the experimental `stage-timingtrace` library (SHA-256 `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`) with the relay from detached checkout `66e054c`, using `--start-timingtrace`. System `fprintd` loaded the experimental library and enumerated the reader. No PAM or SDDM changes.

`fprintd-verify -f left-index-finger` returned `verify-match (done)`.

Recorded monotonic-event intervals:

| Interval | Duration |
| --- | ---: |
| worker start → gateway ready | 731.819 ms |
| gateway ready → contact observed | 773.426 ms |
| contact observed → image captured | 28.472 ms |
| image captured → matcher reply | 6.028 ms |
| cleanup begin → gateway wait complete | **40.168 ms** |
| worker start → verification finished | **1580.185 ms** |

Earlier baseline cleanup took approximately 1,040 ms; this trial reduced it by approximately 96.1%, consistent with removing the one-second blocking daemon-thread join in the Python relay. This establishes a successful single real hardware test, not a statistical matching-accuracy result. The remaining ~732 ms gateway start is considered acceptable and is not a current optimisation priority. The 773 ms between ready and contact includes human placement time and any detection polling latency.

User confirmed rollback of the *previous* trial, then activated this relay-fixed trial. A rollback of this latest live trial has not yet been reported. The reversible command is `bash "$HOME/Projects/ft5955-relay-latency-test/tools/ft5955_kde_trial.sh" --stop`.

No new enrolment needed. This bridge remains lab-only and must not be used for PAM/SDDM authentication without separate security work.
