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

## Five-round bounded retry tester hardware result (18 October)

User ran `ft5955_retry_timer.py --finger left-index-finger --rounds 5 --retries 3` with the experimental driver active. Results: five of five rounds eventually MATCHED, four on the first verification, one after two terminal NO_MATCH results. Total seven verifications: 5 MATCH, 2 NO_MATCH. User deliberately presented a wrong finger during one negative result (the exact attempt is not labelled). Per-round elapsed: 2.176 s, 1.269 s, 1.169 s, 5.765 s, 1.218 s. Full tester elapsed: 16.799 s. **Five out of five completed rounds does not imply 100% per-press recognition**; the bounded retry UX succeeded on this small test.

Timing traces intermittently returned `n/a`; in round 4 the reported previous-verdict-to-next-contact of 6798.6 ms exceeded previous-contact-to-next-contact of 5390.1 ms. Those comparisons cannot both refer to the same preceding physical scan. Current follower queue/last-event map is not robustly correlating complete event groups to individual verification operations, likely due to delayed events. Do NOT present inter-press timing values as trustworthy until event grouping is fixed. Next engineering priority: session-scoped event collection/correlation and a synthetic multi-attempt delayed-journal test, not sensor/matcher speed tuning. No biometric data logging, no PAM/SDDM changes.

## Right-index five-round test with cursor-based timing collector (18 October)

User re-enrolled right index finger in KDE with markedly less placement-error feedback (one such error by user report), then ran the GitHub timing tester from commit `75ceaaa` with `--finger right-index-finger --rounds 5 --retries 3`. **All five rounds matched on their first verification, no NO_MATCH**; a small, uncontrolled test, not a formal accuracy or negative-finger test. The cursor-based timing collector delivered all four per-attempt stages across five rounds, with no `n/a` values. Previous-contact intervals were 7066.1, 2698.9, 2069.9, 2022.0 ms; these are contact-to-contact, **not release-to-next-contact**.

| Round | CLI duration (s) | Gateway startup (ms) | Contact→image (ms) | Image→reply (ms) | Reply→verify finish (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4.448 | 742.2 | 29.3 | 7.2 | 40.4 |
| 2 | 5.909 | 788.1 | 30.4 | 6.9 | 40.8 |
| 3 | 1.521 | 780.0 | 28.4 | 6.5 | 40.6 |
| 4 | 0.916 | 774.8 | 25.6 | 55.0 | 40.9 |
| 5 | 0.916 | 780.2 | 25.9 | 127.7 | 40.4 |

Summary: 5/5 rounds matched first attempt; 18.908 s total tester elapsed, 3.141 s average round time (includes journald retrieval and waits). Mean gateway startup 773.06 ms; mean contact→image 27.92 ms, image→reply 40.66 ms, reply→finish 40.62 ms, total contact→finish about 109.2 ms. Timing stage collection is **observationally improved**; no NO_MATCH occurred in this run, so the post-rejection event-correlation path still warrants a focused test if needed. No driver changes or PAM/SDDM login.
