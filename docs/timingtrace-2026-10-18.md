# FT5955 monotonic stage trace — 18 October 2026

**Status:** source-only diagnostic ready on `feature/ft5955-timingtrace`; GitHub Actions synthetic/offline tests passed. **No live C compilation or real fingerprint timing trace has yet been reported.** This branch is experimental. Keep `main`, the original 500-ms staged driver, the 100-ms staged driver, and the verified early-capture staged driver untouched.

## What it measures

The opt-in `--trace-timing` option applies the proven source reconstruction, 100-ms polling adjustment and concurrent early-capture change inside a **disposable** libfprint source checkout, then adds *only fixed phase names and monotonic microsecond timestamps* to GLib's `g_message` journal. This deliberately **does not change the match-report/cleanup order yet**.

| Phase | Meaning |
| --- | --- |
| `worker_start` | libfprint's operation worker starts |
| `gateway_ready` | concurrent MOH setup received `READY 1` |
| `scan_begin` | the worker starts waiting for an observed fresh touch |
| `first_status_present` / `first_status_absent` | first hardware status observed within a scan |
| `contact_off_observed`, `contact_on_observed` | fresh-touch gate transitions |
| `image_captured` | `0x81` image transfer, frame validation/conversion succeeded |
| `matcher_reply_received` | the gateway returned a response to the image |
| `matcher_match`, `matcher_no_match`, `matcher_quality_retry` | classification of gateway reply |
| `cleanup_begin` | worker entered common shutdown/zeroing path |
| `gateway_wait_complete` | MOH gateway subprocess is reaped |
| `worker_return` | worker scheduled GLib task completion |
| `verify_finish_start`, `verify_finish_done` | main-loop libfprint verify result callback began/ended |

A matching operation's rough **MOH + IPC time** is `matcher_reply_received - image_captured`. The time spent in the driver's **common worker cleanup** is `worker_return - cleanup_begin`; `gateway_wait_complete - cleanup_begin` is a substantial part of it. `verify_finish_start - worker_return` is the task callback scheduling delay. Compare these before moving any callback or changing teardown.

Logs do **not** include raw fingerprint images, templates, fingerprints, user identities, confidence scores, USB packets, image properties or firmware identifiers. Outcome category (`matcher_match`, etc.) is intentionally logged locally. Do not publish unrelated full system journal logs.

## Build and stage separately (no USB, sudo, PAM or installed driver modification)

Run as your normal Linux account:

```bash
TRACE="$HOME/Projects/ft5955-timingtrace-build"
git clone --depth 1 --branch feature/ft5955-timingtrace \
  https://github.com/Inforce855/focaltech-5955-linux.git "$TRACE" &&
python3 "$TRACE/tools/verify_ft5955_clean_clone.py" --stage --trace-timing
```

The staged library is **`~/.local/state/ft5955-system-trial/stage-timingtrace`** with its own SHA-256 file, not `stage-earlycapture`. Refuses to overwrite an existing staged variant or source clone.

## Optional short-lived trial (only after clean build/stage)

If an earlier trial is still active, stop it before starting the new one. These commands assume your existing early-capture short-lived trial, and use the same confirmed rollback pattern; review any unexpected safety-guard failure instead of overriding it.

```bash
EARLY="$HOME/Projects/ft5955-earlycapture-build"
TRACE="$HOME/Projects/ft5955-timingtrace-build"
bash "$EARLY/tools/ft5955_kde_trial.sh" --stop &&
sudo systemctl stop fprintd.service &&
bash "$TRACE/tools/ft5955_kde_trial.sh" --start-timingtrace
```

No re-enrolment. No PAM, SDDM or login integration. With the service activated, perform a **single** `fprintd-verify -f left-index-finger`. After the verification prompt, wait about a second; place the finger normally, hold it for 2–3 seconds, then lift. Note when the terminal's `verify-match` or `verify-no-match` appears, or whether no result arrives. A second sample is optional if the first is ambiguous.

Collect **only timing marker lines**, e.g. run this after a verification attempt:

```bash
sudo journalctl -b -u fprintd.service --since "5 minutes ago" --no-pager -o cat |
  grep 'FT5955TIMING'
```

Share only these filtered lines and the `fprintd-verify` result, not fingerprint images or general journald output. If the filter prints nothing, report that fact—**do not** turn on debug dumps or enable new firmware commands.

Rollback at the end, using the tested script:

```bash
bash "$HOME/Projects/ft5955-timingtrace-build/tools/ft5955_kde_trial.sh" --stop
```

A complete analysis will determine whether the delay is *before image acquisition*, *in MOH matching*, *during sandbox teardown*, or *between worker completion and fprintd reporting*. Timing is not yet evidence of a specific root cause, and this instrumentation should not alter authentication semantics.

## Safety and controlled changes

- Existing libfprint release `1.94.100`, FocalTech `2808:5955` source snapshot and its SHA-256 manifest remain immutable; upstream patches are verified before disposable source modifications.
- The on-wire commands remain `0x82 73 01`, `0x80 01 02`, `0x81`; the finger-off then finger-on rule, 100-ms polling, and 10-ms image settle are unchanged.
- MOH remains isolated as a user process, and the trusted PAM/login path remains unmodified. No Windows driver GPIO `0x37` or `0x80` selector `0x02` introduced.
- Original `--stop` cleanup is unchanged. The diagnostic logs timestamps but **does not remove or bypass subprocess cleanup**.
