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

## Informal repeated-use check, 18 October 2026

User subsequently ran 15 `fprintd-verify -f left-index-finger` commands with the relay fix active. Results, in order: NO_MATCH, NO_MATCH, MATCH, MATCH, MATCH, MATCH, MATCH, NO_MATCH, NO_MATCH, MATCH, MATCH, MATCH, NO_MATCH, MATCH, MATCH. **10/15 match (66.7%); 5/15 no-match (33.3%)**. The final match was visible but its shell timing was truncated. User said the reader now feels **very fast**, but physical finger placement is sometimes awkward because the sensor is recessed/positioned in the power button and requires stretching. This is an uncontrolled usability observation, not an independent measure of false-rejection probability or an accuracy improvement. The previous relay fix affects verdict-delivery latency, not the matcher itself.

User prefers an ordinary authentication UX with a bounded retry after NO_MATCH, rather than restarting the CLI command. Do not implement PAM/SDDM login at this stage; first design bounded retries with password fallback and preserve terminal no-match semantics. No new enrolment or further speed tuning required. Latest experimental installation remains active until explicit reported rollback.

## Planned bounded retry timing tester

User requested a dedicated repeatable tester that retries after genuine `verify-no-match` (maximum three distinct verification operations by default) and displays elapsed time. Record monotonic total duration from test start to final success/failure, separate gateway-ready time, contact-to-capture, matcher verdict and cleanup when available, plus individual attempt outcomes and timings. Make clear that one fprintd verification returning terminal `no-match` requires a new verification operation, not coercion of that status. Distinguish verification attempts from physical presses: fprintd events alone may not establish an exact press count. No biometric material in output. Use normal system fprintd only in the existing lab trial, no PAM or SDDM modifications, and preserve explicit bounded cancellation, rollback and password fallback for any future authentication UX. This is a proposal, not implemented or hardware-tested.

## Further timing display requirement (18 October)

User specifically wants **between-finger-press timing**, rather than only total elapsed time or per-verification duration. Proposed display must distinguish contact→verdict, physical release→next contact, verdict→next contact, initial arming/gateway READY, and final total. The present event-only driver logs first OFF, observed ON, capture and reply but not necessarily each subsequent release: exact inter-press gaps need new low-overhead OFF/ON transition instrumentation with a shared monotonic clock across retries. If multiple CLI verification sessions are used, correlate by test/session ID and correctly handle worker restarts. Do not infer a physical press from a terminal NO_MATCH alone. No raw sensor images or templates in logs. Requirement documented; implementation pending.
