# FocalTech 2808:5955 — experimental Linux fingerprint driver

Linux `libfprint` driver research for the built-in FocalTech USB fingerprint reader **VID:PID `2808:5955`**, tested on **Nobara 44**. The code includes a reproducible driver build, a reversible system-`fprintd` trial and a user-session bridge to the proprietary Windows MOH matching engine.

**Current project state (19 October 2026):** USB capture, `libfprint` / normal `fprintd`, enrolment, real MOH matching and **KDE fingerprint screen unlocking have all worked on the user's Nobara host**. The previously measured ~1-second verdict cleanup delay has a **verified fix**: remove `up.join(timeout=1)` from `tools/ft5955_engine_broker.py` (original commit `66e054c` on the latency branch). The exact previously tested source and the synthetic regression test have now been restored on `main` **and** the existing KDE development branch. **The protected installed copy was subsequently verified as the old version and replaced with that exact tested fix, retaining a backup; post-deployment verification has now succeeded following restoration of the inactive MOH socket and the user's left-index re-enrolment; see the latest live-verification note below.** The isolated engine is still experimental, and secure production authentication has not been approved. Do not reinstall, re-enrol, modify PAM or re-open old polling/retry investigations without evidence.

**Source recovery update (28 October 2026):** All 135 source files in 16 downloaded archives and the standalone scaffold script have been byte-matched to historical GitHub source; the two extra v0.6.1 members were generated Python bytecode. The 11 untracked local-main files and nine modified MOH/source-history files have been reviewed: differences not already represented on GitHub are local directory-path corrections, plus an `.aider*` exclusion in `.gitignore`. **No dirty worktrees or research branches were deleted.**

**Installed baseline verified (28 October 2026):** the active trial library file has the known-good verify-only SHA-256 `02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28`, and `git hash-object` of the installed `ft5955_engine_broker.py` returned Git blob `6fa2dcf7ece70cabab19b9e2825f2255fa437a3f`, matching the committed one-second-fixed broker exactly. This is read-only file/configuration verification, **not** a new security certification or post-audit live hardware test. The installed development relay was subsequently matched byte-for-byte to `tools/ft5955_dev_relay.py` on the existing `feature/kde-lock-auth-preflight-20261018` branch (Git blob `fd6cb387e1a923021100c5a95ceac35a5d4e1fbf`), which must be preserved until maintained-source consolidation. Multi-template `identify`, MOH trust controls and a supported non-`dev` release remain outstanding. **Do not delete branches or replace the working driver**; see the [reconciliation checkpoint](docs/source-reconciliation-2026-10-28.md).

[**Project status / next action**](PROJECT_STATUS.md) · [**All branches and their purpose**](docs/BRANCHES.md) · [**Measured relay timing and five-round tests**](https://github.com/Inforce855/focaltech-5955-linux/blob/feature/ft5955-relay-latency/docs/relay-latency-hardware-pass-2026-10-18.md) · [**Independent engine hardware verification**](https://github.com/Inforce855/focaltech-5955-linux/blob/feature/kde-lock-auth-preflight-20261018/docs/ft5955-dev-real-service-handoff-2026-10-18.md)

**Historical milestone (17 October 2026):** an end-to-end KDE *enrol/verify* experiment succeeded, with successful rollback. The old deployment and PAM statements in the dated sections below describe that historical 17 October baseline, **not** the host's later 18 October status or current active service.



**Deployment update (19 October 2026):** The user's read-only `git hash-object` check proved the protected installed relay at `/opt/ft5955-dev/ft5955_engine_broker.py` was the earlier `68035014f464d6b5de8941adc00e6afd15c5719c` version, which still contained the ~1 s cleanup join. A guarded replacement installed the **exact previously hardware-verified fixed source** (Git blob `6fa2dcf7ece70cabab19b9e2825f2255fa437a3f`) and reported **PASS**, saving the original as `/opt/ft5955-dev/ft5955_engine_broker.py.before-1s-fix`. No service restart, fingerprint enrolment, PAM, KDE or libfprint configuration change was made. **A post-installation verification operation has not yet been reported.** This is a restored known fix, not a new design or approval for security-critical production login. See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the next step.

**Reboot verification (19 October 2026):** User confirmed the working fingerprint setup **survived a full reboot** after enabling `ft5955-engine-dev.socket` at startup. This is a user-reported operational milestone (no post-reboot CLI log was pasted). Previous 7/7 post-re-enrolment left-index matches and the corrected relay remain the verified hardware baseline. Next: consolidate installed components, existing guarded setup/rollback and documentation; review experimental MOH/template trust limitations before any claim of secure production KDE/PAM authentication. No further basic matching or latency tests are needed.

**Latest live verification (19 October 2026):** After the protected `ft5955-engine-dev.socket` was discovered **inactive** despite the development trial markers remaining active, the user manually started the **existing** socket and restored normal fingerprint decisions (no-match and match instead of broken pipe/unknown error). The user then re-enrolled the left index finger because the previous enrolment performed poorly. Of 18 chronological CLI results shared, the first 11 were **2 matches / 9 no-matches**, followed by **7 consecutive matches / 0 no-matches** (the before/after boundary follows the user's description; the enrol command itself was not included). Median shell elapsed time for the final seven matches was **518 ms**. No PAM changes or repeated speed tweaks were required. The installed source is the previously verified fixed broker and the original remains backed up; the socket was manually started, and its **boot enablement is not yet verified**. This is real end-to-end matching success in an **experimental** integration, *not* validation of biometric storage integrity or approval for production KDE/PAM login. See [PROJECT_STATUS.md](PROJECT_STATUS.md).

**Live privileged-authentication milestone (19 October 2026):** After enabling global `authselect with-fingerprint`, the user confirmed successful **Polkit (`pkexec`) and `sudo` fingerprint authentication** using the **right index finger**, through the current protected UID955 MOH service. The left index also remains enrolled, but the PAM `any` path currently selects the right: the checked driver snapshot supports `verify` without `identify`. This proves actual privileged-authentication functionality, but **not** password-fallback-after-activation, multi-finger identification, KDE locker behaviour or production trust/security approval. Preserve the named authselect rollback `ft5955-pre-fingerprint-20261019-113538`; retire `-dev` only after a tested supported replacement is prepared.

**Live KDE milestone (19 October 2026):** User reports successful **fingerprint unlocking of the KDE screen** with global `authselect with-fingerprint` enabled. Together with separately confirmed successful Polkit (`pkexec`) and `sudo` fingerprint authentication, this completes the initial functional KDE/PAM integration milestone on the actual Nobara hardware. The finger used for screen unlock and post-activation screen-lock password-fallback test were not specified; avoid extrapolating multi-finger success or comprehensive security approval. Remaining engineering requirements are either-index `identify` support, accurate cancellation/claim recovery, a maintained non-`dev` installer/service with rollback, and MOH/template/sandbox trust review. Preserve the named authselect backup `ft5955-pre-fingerprint-20261019-113538` and existing working configuration.

## Intended KDE authentication completion

**User-confirmed finish line (19 October 2026):** fingerprint support for **KDE screen locker/screensaver unlock**, **KDE Polkit authorisation dialogs**, and an optional separately assessed **sudo** authentication path, all with reliable password fallback. Initial display-manager login is a separate integration decision. Ordinary `fprintd-verify` success and survival of the MOH socket after reboot are **necessary but not sufficient**. The existing UID955 MOH service and template handling have outstanding authenticity, identity binding, sandbox and vendor-`UNVERIFIED_ATTACH` security questions. Do not blindly install `fprintd-pam`, turn on global authselect `with-fingerprint`, change `system-auth`, or remove the lab-script safety guard to reach a lock-screen prompt. Begin with the existing read-only KDE/PAM preflight (see `tools/ft5955_kde_auth_preflight.sh` on the KDE feature branch), review effective per-service PAM flows, then implement narrowly scoped, reversible changes only after the trust boundary is validated. Avoid repeating solved sensor, timing, enrolment and matching work.

## Verified on the actual device

| Milestone | Observed result |
| --- | --- |
| USB handshake, finger contact/release, and 64 × 80 image acquisition | **PASS** on physical `2808:5955` |
| Private `fprintd` device Claim/Release, enrolment and matching | **PASS** in controlled tests; genuine rejections intermittently occurred |
| Different-finger rejection and stored-template cross-daemon restart | **PASS** in limited tests; not security assurance |
| Clean-clone libfprint v1.94.100 rebuild from three verified patches | **PASS**: pinned upstream commit, 109/109 Ninja steps; not full test suite |
| Actual Nobara system `fprintd` loading experimental shared library | **PASS**, verified from process mappings and system D-Bus |
| KDE System Settings → Users fingerprint enrolment | **PASS**: user registered **left and right index fingers** |
| Normal `fprintd-verify` | **PASS**: genuine `verify-match` observed; user estimates ~85% success *after 3–4 separate taps*, **not** 85% first-touch accuracy |
| Reversible system installation and removal | **PASS**: trial files and service override removed; vendor RPM files unaffected; original Nobara configuration restored |
| Secure PAM/SDDM fingerprint login | **NOT enabled or validated** |
| Fully native Linux matching, without proprietary DLL | **NOT complete** |

The matching-engine bridge runs the existing pinned vendor DLL in the **user's isolated bubblewrap environment**, connected through an experimental AF_UNIX broker. It does **not** execute the Windows engine as root. The vendor's diagnostic `FT5955_ALLOW_UNVERIFIED_ATTACH` flag, user-controlled matching process, template-integrity limitations and inconsistent recognition are barriers to security-critical login.

**No further enrolment or repeated hardware-baseline tests are needed to establish this milestone.** The user has saved a Timeshift snapshot as an additional recovery measure, but the explicit driver rollback already **passed**.

[Complete dated KDE test and rollback record](docs/kde-short-lived-trial-2026-10-17.md) · [Roadmap](docs/roadmap.md) · [Next-session handoff](docs/next-session-handoff.md) · [Documentation index](docs/index.md)

## What is current

| Purpose | Source |
| --- | --- |
| Immutable, provenance-checked driver snapshot, header sources and matching bridge | [`driver/live-snapshot-2026-10-16/`](driver/live-snapshot-2026-10-16/README.md) |
| Independent upstream clone, hash verification, patch application, build and optional stage | [`tools/verify_ft5955_clean_clone.py`](tools/verify_ft5955_clean_clone.py) |
| Reversible **discovery-only** system-`fprintd` trial | [`tools/manage_ft5955_system_trial.sh`](tools/manage_ft5955_system_trial.sh) |
| Short-lived **experimental KDE enrol/verify** activation and rollback | [`tools/ft5955_kde_trial.sh`](tools/ft5955_kde_trial.sh) |
| System-side KDE trial installer and removal guard | [`tools/manage_ft5955_kde_trial.sh`](tools/manage_ft5955_kde_trial.sh) |
| Existing original MOH sandbox + fingerprint matcher | Locally maintained **outside** this repository; proprietary DLL **not distributed** |
| Historical private-`fprintd` tests and original research | [`experiments/private-fprintd/`](experiments/private-fprintd/README.md), [`research/source-history/`](research/source-history/), [archived research](docs/archive/) |
| Native C image-processing / matching investigation | [`native/`](native/README.md) |

The dated driver snapshot and its three build patches are intentionally preserved; avoid editing them casually. Historical experiments are reference material, not instructions to rerun against the live system.

## Reproducing the source build (no fingerprint scan)

The tested independent builder reconstructs the driver from an upstream `libfprint v1.94.100` clone using the verified scaffold, USB descriptor and final source patches. The checked upstream commit is `80a4b5ec612892c5c056c48dddaa561452cf37ec`. The build was independently completed on Nobara 44; its test-suite dependencies were not all present, so do **not** equate 109/109 build steps with a full test-suite PASS.

```bash
# Source-only checks, without privileged actions or USB access:
python3 tools/verify_ft5955_clean_clone.py

# Optional: network fetch, independent compile in disposable temp directory:
python3 tools/verify_ft5955_clean_clone.py --build
```

The **`--stage`** option additionally creates a verified user-owned compiled library for an **explicit separate** reversible install. The historical `--claim-only` option exercises real USB through private `fprintd`: **do not** run that as a routine build check.

## Reversible experimental system integration

The user already ran and completed the following cycle **successfully** on 17 October:

1. Build and stage the experimental library without replacing the packaged RPM library.
2. Start the known user-owned MOH/bwrap bridge and temporarily configure **normal** `fprintd` through [`tools/ft5955_kde_trial.sh --start`](tools/ft5955_kde_trial.sh).
3. Register left/right index fingers in KDE; obtain real `verify-match` with standard `fprintd-verify`.
4. Run `tools/ft5955_kde_trial.sh --stop`, which removed the relay and experimental root-owned `/opt` shared library and drop-in and stopped normal `fprintd`. **Rollback PASS**.

**There is currently no active experimental system driver installation.** The source-only staging artifact may remain in `~/.local/state/ft5955-system-trial/stage`. Fingerprint templates created by KDE may still exist in normal `fprintd` storage; rollback does not delete them. No PAM, SDDM or login change was made.

The KDE scripts are **lab-only** and require the exact known Nobara packages, a working local proprietary sandbox and user approval for temporary privileged service changes. They are **not** a ready-to-install release or a supported authentication method. See the [actual tested commands, results and rollback](docs/kde-short-lived-trial-2026-10-17.md) before attempting further work.

## Next technical priorities

1. Improve **single deliberate press** reliability. The user clarified (18 October) that **rapid tapping** works better than a deliberate lift, wait and press. The present driver checks contact every **500 ms**, requires an observed release before accepting a press, and then waits only **10 ms** before requesting an image. A separate opt-in **100-ms polling / 1,200-check** test build now exists with a **separate staged library**, keeping the original two-minute bound and original snapshot unchanged. It passed offline source checks but **not yet** real sensor recognition testing. See the [timing handoff](docs/next-session-handoff.md) and `--poll-100ms` builder option; no new enrolments are necessary to test it.
2. Review authenticating and storing templates, cancellation/timeout behavior and the trust boundary before any PAM/SDDM/login integration. Do not silently weaken the fprintd service or interpret a no-match as success.
3. Develop and verify the native matcher. The Windows MOH DLL (although pinned and isolated in laboratory testing) remains a proprietary dependency, and the current experimental attach flags are not approved for production login.
4. Once secure and reliable, design a **maintained, reversible installer** tested on the actual system. Do not equate the successful one-off lab trial with a finished distribution package.

Source provenance, earlier failed attempts and temporary workaround history are recorded in the [documentation index](docs/index.md). Do not commit biometric image files, fingerprint templates, raw captures, DLLs, local private logs or user credentials. Other FocalTech product IDs are **not** known to work.

**Licence:** The repository has no project-wide `LICENSE` yet; individual files carry their own licence headers. Do not assume the entire tree is available under a single licence.
