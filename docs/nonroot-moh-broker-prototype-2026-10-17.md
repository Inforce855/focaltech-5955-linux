# Non-root matching-engine IPC broker — initial source prototype

**17 October 2026 · Synthetic protocol smoke test PASSED in GitHub Actions. No new driver installation.**

## Why the normal system driver cannot simply use the experimental engine

- The reproducibly built FocalTech libfprint loaded and **normal system `fprintd` GetDevices succeeded** using our reversible `/opt` installation. The full service trial and rollback passed. It **deliberately set** `FT5955_EXPERIMENTAL_ENABLE=0` and removed `FT5955_ENGINE_GATEWAY`.
- In [`ft5955_native_action.c`](../driver/live-snapshot-2026-10-16/libfprint/drivers/ft5955_native_action.c), enabling biometrics makes the normal fprintd process launch `/usr/bin/python3 <FT5955_ENGINE_GATEWAY>` as a child. The system service has no `User=`, so this process would be **root**.
- [`engine_gateway.py`](../driver/live-snapshot-2026-10-16/engine/engine_gateway.py) correctly refuses root, and the proprietary runner and DLL currently live in the developer's home tree. Nobara's normal system unit has `ProtectHome=yes`, hiding `/home` and `/run/user`. Simply exposing those directories or removing the root refusal is **not an acceptable integration**.
- Also, the existing template envelope's unkeyed checksum is not an authenticity guarantee. KDE login/password authentication must remain untouched while this boundary is unresolved.

## Proposed limited design

We added [`tools/ft5955_engine_broker.py`](../tools/ft5955_engine_broker.py), a standalone experimental **AF_UNIX broker and stdio relay** that is not yet enabled in any systemd unit.

1. **Root fprintd** may eventually launch a *root-owned, audited relay* as a short-lived Python child, via the existing `FT5955_ENGINE_GATEWAY` hook. The relay **never imports/loads proprietary code** and only forwards bounded chunks of binary protocol between standard input/output and one socket at `/run/ft5955-engine/engine.sock`.
2. A **dedicated non-root** systemd service (service account to be created later, not the login user) would be started via a socket unit with `SocketGroup=root`, `SocketMode=0660`, under `/run/ft5955-engine`. The broker receives listening fd 3 through socket activation. It accepts **only root-UID peers**, using Linux `SO_PEERCRED`. The dedicated account must have read-only access to a separately secured audited MOH runner/engine directory, **not access to arbitrary home files**.
3. Each accepted session launches the already tested `engine_gateway.py` under the dedicated non-root account with a minimal subprocess environment. Its individual MOH subprocess remains isolated by its existing bwrap rules, with bounded read and cleanup on peer/child exit.
4. **Production not authorised:** until verified with the actual systemd sandbox, review root-owned script deployment, bwrap availability, socket permissions, cancellation/timeout, honest matcher results, secure template persistence and login fallback. Neither test-mode broker nor synthetic gateway may ever be used for real biometric authentication.

## Runner audit — user-provided 17 October source

The user's **real local** `test_moh_isolated_live_identify.sh` was inspected by printing its first 260 lines and running `bash -n`; syntax returned cleanly. The full displayed file establishes:

- It changes directory to its parent source tree: `cd "$(dirname "$0")/.."`, then imports `tools.moh_engine_preflight` and compiles `engine/ft_engine.c` and numerous `engine/ft5955_compat_*.c` files. **A DLL alone is insufficient**; the separate non-root service needs the audited C and Python dependencies in a stable read-only tree, or a precompiled reproducible executable.
- With no argument it takes **`/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll`** as the DLL. The path is merely a **default**, not proof that the DLL exists; it accepts a positional DLL or ZIP. Our current `template_runner.py` passes no explicit DLL, despite having an `executable` Python parameter. A future service-specific copy should pass an explicit root-owned DLL path, with the pinned SHA audit still intact. Do **not** edit the immutable saved 16 October snapshot.
- `moh_engine_preflight.audit(candidate, Path("engine/ft_engine.c"))` requires **exactly 110 covered imports** and a SHA-256 match with the module's pinned DLL digest; it then hashes the actual temporary engine copy before any execution. This is stronger than just trusting a filename, but the user's printed source does **not** prove the currently installed DLL is present or matches. The read-only [relocation preflight](../tools/audit_ft5955_moh_relocation.py) checks those facts.
- The runner compiles an executable in mode-0700 disposable `/tmp`, then uses `timeout --signal=KILL 1200s bwrap --unshare-all --die-with-parent --new-session --clearenv`, a read-only host runtime, private `/tmp`, and read-only binds of **only** the verified DLL and built executable. No host `/home`, real USB device, network, or other host writable paths are mounted. The code needs functioning **unprivileged user namespaces** in the eventual `ft5955-engine` service context; this cannot be established by reading the script alone.
- The GCC flags explicitly include `-DFT5955_ALLOW_UNVERIFIED_ATTACH` and other `FT5955_OFFLINE_...` mock/diagnostic flags. Those guards may be required by the experimental MOH path, but **they must not be misrepresented as production-authentication readiness**. The service can be validated as a laboratory experiment with PAM disabled while remaining unsuitable for high-trust login.

The retained date-stamped C/native driver and three reproducible source patches are **unchanged**.

## Non-installed systemd prototypes

- [`systemd/ft5955-engine.socket`](../systemd/ft5955-engine.socket) proposes a root-group `0660` Unix socket outside /home. Systemd would own the listening descriptor and pass fd 3 to the broker, allowing only root clients and the dedicated service account to connect.
- [`systemd/ft5955-engine.service`](../systemd/ft5955-engine.service) proposes a separate `ft5955-engine` non-root account with `ProtectHome=yes`, `ProtectSystem=strict`, `PrivateDevices=yes` and no Linux capabilities. It expects audited engine code under root-owned `/opt/ft5955-system-trial/engine` and a private MOH tree under `/var/lib/ft5955-engine/vendor`. **These do not exist yet**; this is not an installer.
- `NoNewPrivileges=yes`, user namespaces and the local MOH bwrap runner may interact; we have not validated that the proprietary loader will run under the proposed sandbox. The prototype service may need narrower researched allowances after source-only runner audit. **Do not weaken protections blindly.**

## Current offline check

**GitHub Actions passed** the `FT5955 broker synthetic transport` Python syntax + mock protocol check (run [39024071118](https://github.com/Inforce855/focaltech-5955-linux/actions/runs/39024071118), status `completed`, conclusion `success`). CI is **synthetic only**: it uses no fingerprint reader or proprietary engine and does not establish security of fingerprint recognition.



The accompanying [`tools/test_ft5955_engine_broker_synthetic.py`](../tools/test_ft5955_engine_broker_synthetic.py) launches both halves **only as the ordinary user**, with a disposable `/tmp` socket protected by a private directory. Its fake gateway accepts a synthetic all-zero 5,120-byte payload and emits **`READY 1`**, **`RETRY QUALITY`**, then **`BYE`**. It **never emits `MATCH`**, never accesses USB/fingerprints/templates/DLLs, and leaves fprintd/systemd/PAM unchanged. Passing it validates only transport, not recognition/security/integration.

```bash
REPO="$HOME/Projects/ft5955-independent-build-check"
git -C "$REPO" pull --ff-only
python3 -m py_compile "$REPO/tools/ft5955_engine_broker.py" \
                      "$REPO/tools/test_ft5955_engine_broker_synthetic.py"
python3 "$REPO/tools/test_ft5955_engine_broker_synthetic.py"
```

**Next after synthetic pass:** consider packaging the privileged relay and dedicated non-root systemd broker behind the existing explicit install/rollback guard, with the normal `FT5955_EXPERIMENTAL_ENABLE` still disabled. Test service isolation without any fingerprint scans before an enrolment through KDE. The previous successful private D-Bus and native-action tests remain the baseline; don't repeat them needlessly.

The dated live driver snapshot and its three source patches were **not changed** by this prototype.
