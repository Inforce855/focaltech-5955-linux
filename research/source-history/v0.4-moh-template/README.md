# FT5955 — Template restart boundary v0.4 (14 October 2026)

**Experimental / private / local only. Not a working libfprint driver.**

## Why this exists

The working v0.3 IPC test was confirmed on the physical 2808:5955 reader:
12 successful MOH enrolment stages for each of two fingers, plus four correctly
labelled live identification tests. That is a genuinely working RAM-only
identification pipeline. It does **not** prove that a template will survive an
engine restart or can be serialised as a libfprint `FpPrint`.

This test targets that precise gap without adding more unrelated NBIS work or
re-running the already proven two-finger live test:

1. Enrol **one finger** through the original 8-touch-bounded USB helper (12
   successful impressions total; rejected impressions do not count).
2. Call the known-good `ft_engine_enroll_commit()` and obtain its template bytes
   and subfactor from the temporary sandbox's RAM.
3. Pass the template privately over anonymous local pipes to the normal-user
   supervisor, then close the original engine sandbox.
4. Start a **fresh** independently SHA-validated, bubblewrap-isolated MOH engine.
5. Import the same bytes and subfactor into the fresh engine process and ask it
   to verify a **new** sensor impression. Test same finger and different finger.
6. Wipe mutable in-memory template buffers and terminate the engine process.

**No template is written to disk or printed.** Raw image data flows only
through the existing USB helper and anonymous pipes. Python/OS process-memory
copies are not guaranteed to be securely erased; this experiment is not a
hardened biometric storage implementation.

## Safety / integration boundaries

- `template_session.c`: tiny new C program that uses existing `ft_engine_*`
  functions. Its protocol is one-byte commands `E` + 5120 bytes (enrol),
  `X` (export), `I` + 5-byte header + template (import), `V` + 5120 bytes
  (verify), `Q` (quit). Export is `TEMPLATE size subfactor\n` + exact bytes.
- `template_runner.py`: makes a **temporary copy** of the existing
  `tools/test_moh_isolated_live_identify.sh`, changing ONLY its working
  directory and the test C source filename. The original repository, shell
  runner, installed DLL and GUI are **unchanged**. Its original SHA-256 audit,
  bubblewrap sandbox, no-USB/no-network isolation, and timeout remain in force.
  If the original script's expected lines change, this prototype refuses to run.
- `template_restart_client.py`: the only real-hardware entrypoint. It must be
  launched by a regular user and requires explicit `--live`. It imports the
  exact known-good, inverted `prepared_pixels()` function from the existing
  MOH feature branch. The privileged USB helper stays limited to 8 frames /
  240 status polls per batch.
- No `fprintd`, KDE or PAM changes. No production verification or persistent
  authentication data. **Do not upload raw captures, DLLs or template bytes.**

## First, run the synthetic regression

```bash
cd ~/Projects/ft5955-moh-template-v0.4
bash run_tests.sh
```

The Python unit test compiles `template_session.c` against a **fake** engine
and checks rejected impressions, 12 accepted stages, binary template export,
process restart, import, matching and no-match. No sudo or sensor access.
This test passed in the development container. Real DLL restart compatibility
has **not yet been established**.

## Optional live on-device test (only when ready)

```bash
cd ~/Projects/ft5955-moh-template-v0.4
sudo -v
python3 template_restart_client.py --live
```

- Keep the **same finger** for all 12 accepted enrolment impressions.
- After the program reports a fresh engine sandbox and a successful template
  import, scan the original finger: the hoped-for result is `MATCH 1`.
- Then scan a **different** finger: the hoped-for result is `NO_MATCH`.
- Type `q` to stop; Ctrl+C also interrupts. Do not publish image/template data.
- If it reports `ERROR` or hangs, abort rather than blindly retrying. The
  original v0.3 two-finger identification test remains unchanged.

**A successful test would establish that the vendor template is portable
between separate engine processes for this case**. It would not by itself
establish secure, cross-reboot persistent FpPrint storage, accuracy or a working
native libfprint enrolment driver. The next step would be a versioned, private
`FpPrint` representation plus libfprint callbacks in the separate
`~/Projects/libfprint-ft5955` development checkout.
