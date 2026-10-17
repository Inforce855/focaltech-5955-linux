# FT5955 v0.9.4 — verification cancellation and forced quality-retry test

**Experimental test tools only.** They do NOT edit the working FT5955 driver,
its existing v0.9.2 retry fix, the MOH matcher, the private libfprint library,
fprintd, PAM or the system login stack. They do not persist fingerprint images,
prints or biometric templates. This test requires one real 12-stage enrolment,
kept in RAM throughout both verification checks.

This package supplies four independently reviewable test/build sources (plus a guarded local installer):

- `tests/native_verify_safety_v094.c` — async verification cancellation, USB reopen, and one verification against a RAM-only print.
- `tests/ft5955_quality_proxy_v094.py` — **only during the verification test**, discards the first captured verification frame and emits the protocol reply `RETRY QUALITY` once. The second captured frame goes unaltered to the existing sandboxed MOH matcher via the original engine gateway. The script never reads or stores biometric information to disk and does not connect to the network.
- `tests/test_quality_proxy_v094.py` — offline mock-gateway protocol test (synthetic bytes, no live fingerprints).
- `tools/build_ft5955_verify_safety_v094.sh` — builds the test program against the **existing private** libfprint only.

## Install the test-only source package locally

The package contains fully reviewable C, Python, shell and documentation sources.
The automatic GitHub publication could not be completed, so this archive is the
verified local deliverable. Its installer **refuses to overwrite** existing
v0.9.1 validation files. It does not change the private libfprint driver or
existing Git worktrees. Do not run as root.

Download `ft5955-v094-source.tar.gz`, then from the directory containing it:

```bash
tar -tzf ft5955-v094-source.tar.gz
tar -xzf ft5955-v094-source.tar.gz
bash ft5955-v094/install_into_v091.sh
```

Expect the offline `PASS` followed by compilation and private-libfprint linkage
confirmation. The installer does not launch a live sensor test. See the next
section for the separate opt-in live test.

Optionally, after reviewing the source, you can commit it to your research
GitHub branch from your own clean worktree; no automatic push is performed.
Do not run `git pull` or switch branches in any existing worktree.

## Live test: both remaining paths, only one enrolment

```bash
cd ~/Projects/ft5955-native-validation-v0.9.1
ulimit -c 0
export FT5955_EXPERIMENTAL_ENABLE=1
export FT5955_ENGINE_GATEWAY="$HOME/Projects/ft5955-driver-integration-v0.8/engine/engine_gateway.py"
export FT5955_QUALITY_PROBE_GATEWAY="$PWD/tests/ft5955_quality_proxy_v094.py"
./build-tests/native_verify_safety_v094 --live
```

Sequence:

1. **Normal enrolment.** Finger off initially. Put the *same* finger on the
   sensor until the engine accepts 12 impressions; lift between captures.
2. **Verification cancellation.** Keep your finger **OFF** the sensor and press
   Enter. After three seconds the client calls `GCancellable.cancel`. It must
   receive **`G_IO_ERROR_CANCELLED`**, with **no match callback**, then close
   and reopen the USB reader successfully. A 35-second watchdog makes hangs
   a failure; it does not allow close while a verification is still pending.
3. **Forced verification-quality retry.** Ensure finger is **OFF**, press Enter,
   and touch once with the enrolled finger. The diagnostic gateway *discards*
   this real image (does not send it to the matcher), responding **once** with
   `RETRY QUALITY`. The existing v0.9.2 driver's real retry handler should
   emit **`FT5955 scan rejected; lift and reposition finger`**. **Lift fully**,
   then touch a second time with the enrolled finger to obtain an actual matcher
   response. The client requires **exactly one intercepted driver retry
   message**, **one terminal match report**, and **`MATCH`** in that same
   verification operation. A `NO_MATCH` on the second physical touch is a
   real negative result and fails the diagnostic without implying a driver bug.

No scan is replayed. The quality injection occurs **only in verify mode** and
only on the first scan of that verification. In a running session, the driver
spawns the temporary proxy only for the quality-retry step; the original gateway
path is restored afterward. If the injected retry handling were broken,
libfprint might assert or the operation might fail; do not use this as a system
login driver until investigated.

## Important boundaries

- A successful test verifies two narrow properties: verify cancellation and
  the single-report retry path. **It is not a false-accept-rate validation.**
- A matching enrolment print still lives in process memory and may not be
  physically wiped by GLib deallocation, just as in v0.9.1.
- A hung synchronous quality verification can be interrupted with Ctrl+C;
  that is **not** a successful cancellation result. The fixed diagnostic has
  no auto-timeout for a human-delayed second touch.
- The proxy uses only local stdin/stdout subprocess communication and inherits
  the permissions of the user who runs the validation. It is test-only and
  must never be installed as a production gateway.
- After exiting, check `pgrep -af 'engine_gateway.py|bwrap|ft_engine|ft5955_quality_proxy' || true`.
  No output means there are no matching leftover processes at that moment.
- The USB persist warning (`Failed to disable USB persist`) is a known,
  nonfatal warning in the existing test environment.
- Do **not** add the private driver to the system, or enable fprintd/PAM/KDE
  fingerprint login yet. That needs a separate, reversible, staged trial.

## Validation provenance

The Python gateway was tested offline against a synthetic mock. It confirmed
one injected `RETRY QUALITY`, an unmodified subsequent frame, unchanged
enrolment forwarding and refusal without opt-in. **No live hardware validation
or compilation against the user's specific private libfprint has been performed
in this publication environment.** The user runs those checks before claiming
pass. No patches were applied to any driver source file.
