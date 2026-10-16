# FT5955 MOH IPC mock v0.1

This is a **synthetic, isolated protocol test**, not a fingerprint implementation.
It does not read fingerprint data, contact USB, load the proprietary DLL, write biometric templates or modify installed libfprint/fprintd/PAM.

## Test

```bash
python3 moh_ipc.py --smoke-test
```

The test starts a separate mock subprocess and exercises 12 successful stages, a rejected frame that doesn't advance progress, verify results, cancellation, and shutdown.

## Next integration step

Keep the current `libfprint-ft5955` driver unchanged while implementing a bounded MOH worker interface behind the verified `bubblewrap` launcher in `focaltech-5955-moh-test`. The worker must use the actual `ft_engine_accept`, `ft_engine_enroll_update` and `ft_engine_verify` calls, with in-memory sample delivery. The mock's `VERIFY MATCH` command is **not** a real matching operation and must be replaced before integration.

The libfprint driver eventually needs asynchronous, cancellable USB captures and libfprint `FpPrint` enrol/verify callbacks. A key unresolved task is safely serialising a template and reloading it into an isolated engine on a later session. Preserve the SHA-pinned DLL and do not enable system authentication.

This archive deliberately does not overwrite any existing project files. The mock's line-oriented protocol describes control flow only; real biometric frames should go through length-checked binary transport and not be emitted to logs.
