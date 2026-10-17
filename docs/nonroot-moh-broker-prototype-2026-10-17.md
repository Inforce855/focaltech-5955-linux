# Non-root matching-engine IPC broker — initial source prototype

**17 October 2026 · Prototype code committed; synthetic check awaits execution. No new driver installation.**

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

## Current offline check

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
