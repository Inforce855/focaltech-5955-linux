# FT5955 MOH engine bridge — experimental baseline

## Goal

Run the actual **FocalTech 2808:5955** match-on-host Windows engine under
Linux using an isolated adaptation of the FT9201 PE loader, then integrate its
proven enrolment and verification operations into a normal libfprint FpDevice.
The USB transport and experimental Windows-style 64×80 conversion are already
in the main project; **do not replace them with FT9201 device commands**.

This is NOT yet a working 5955 matcher/driver and makes NO fprintd/PAM changes.

## Source, licence and proprietary files

- Baseline: OMGrant/ft9201-libfprint, src/ft_engine.c / src/ft_engine.h
  (LGPL-2.1-or-later): https://github.com/OMGrant/ft9201-libfprint
- Copied/adapted files: engine/ft_engine.c and engine/ft_engine.h.
  LGPL licence text: engine/COPYING.LGPL-2.1.
- The required proprietary DLL is **not stored in GitHub**. The private original
  MOH ftWbioEngineAdapter.dll SHA256 is
  a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c.
- The matching DLL is from the MOH package for USB VID:PID 2808:5955, not
  the separate MOC/FT9365 engine or the FT9201's own engine.

## Confirmed initial import gap

Read-only static comparison on the exact MOH DLL:

- KERNEL32: 98 named imports.
- ADVAPI32: 7.
- SETUPAPI: 5.
- Total: **110**; existing FT9201 loader registers **69** required names.
- Initially **41 were missing**. The first five added imports are
  QueryPerformanceFrequency, Sleep, GetLocalTime, GetCurrentThread and
  GetConsoleOutputCP. QueryPerformanceCounter also now uses the same real
  nanosecond monotonic clock as QueryPerformanceFrequency.
- **Expected after this patch: 84/110 names covered, 26 still missing**.
  Four FLS APIs now use a pthread-backed per-thread implementation with
  tested thread isolation, re-use and callback cleanup. This does not
  emulate multiple Windows fibers sharing one pthread; that behavior and
  DLL runtime expectations still need validation.
  Presence of a registered shim is not proof that its semantics satisfy this
  different engine.

The original FT9201 loader inserts NULL into the IAT when a shim is absent.
Our local adaptation **fails closed** and does not execute TLS callbacks or
DllMain while any imports remain unresolved. The inherited FT9201 Attach
path (including its hard-coded pipeline/context offsets) is blocked by default
pending verification against the 5955 MOH engine ABI.

## First local test (read-only, no vendor execution)

On Nobara, fetch this feature branch and run:

    cd ~/Projects/focaltech-5955-linux
    git fetch origin
    git switch feature/ft5955-moh-engine-bridge
    python3 -m unittest discover -s tests -p test_moh_engine_preflight.py
    python3 tools/moh_engine_preflight.py /path/to/7_Fingerprint-module.zip

The last command checks that the archive contains exactly one MOH engine,
temporarily extracts that private DLL, verifies its SHA256, calls objdump on its
import table, compares imports to registered loader shims and cleans up.
You can alternatively supply the private MOH DLL path directly.

Its expected current result is **84/110 covered, 26 missing** and exit status 1.
That exit status indicates a *correctly enforced import gate*, not a test crash.
No USB calls, enrolment, fingerprint images, templates or authentication changes.

The narrow C time/thread compatibility tests also run without a DLL or USB:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_time.c tests/test_moh_compat_time.c \\
      -o /tmp/ft5955_compat_time_test
    /tmp/ft5955_compat_time_test

The four FLS shims also have an isolated C test:

    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_fls.c tests/test_moh_compat_fls.c \\
      -o /tmp/ft5955_compat_fls_test
    /tmp/ft5955_compat_fls_test

The new restricted locale LCID functions (GetUserDefaultLCID,
IsValidLocale) intentionally support only en-GB, en-US and invariant
identifiers; they are **not** complete Windows NLS implementations and other
locales fail closed. The isolated locale test is:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_locale.c tests/test_moh_compat_locale.c \\
      -o /tmp/ft5955_compat_locale_test
    /tmp/ft5955_compat_locale_test

EnumSystemLocalesW now emits only the Win32 locale identifier strings for
en-US and en-GB (installed-only mode advertises the configured English
locale), passing the callback with the Windows x64 ABI. A callback that
returns FALSE stops enumeration without error, as documented by Microsoft.
It deliberately does not claim to enumerate every actual Windows-supported
locale or support alternate sort IDs; the real DLL's needs remain unknown.
Static coverage improves by one, not runtime readiness.

Offline synthetic enum callback test:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_locale.c engine/ft5955_compat_locale_enum.c \\
      tests/test_moh_compat_locale_enum.c -o /tmp/ft5955_locale_enum_test
    /tmp/ft5955_locale_enum_test

GetLocaleInfoW now supports only a fixed subset of English/invariant
strings (date/time formats, decimal and grouping separators, locale name,
etc.). Unknown locale types or modifier flags fail instead of returning
fabricated data. See Microsoft's GetLocaleInfoW contract for buffer sizing.
Test this separately:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_locale.c tests/test_moh_compat_locale_info.c \\
      -o /tmp/ft5955_compat_locale_info_test
    /tmp/ft5955_compat_locale_info_test

**Important:** 84/110 means **registered API names**, not 83 APIs fully
compatible with the real DLL. The inherited FT9201 shims contain mock
Windows handles, no-op critical sections and other approximations whose
semantics must be audited before any engine execution. Even the new locale
and date-format shims implement only documented narrow subsets. Import-name
coverage is a tracking metric, **not an execution readiness score**.

GetDateFormatW and GetTimeFormatW now have deliberately conservative UK/US/
invariant default-format support: custom date/time patterns and unknown locale
settings return failure rather than silently returning fabricated output.
This is a **partial API implementation**, not yet evidence the MOH DLL uses
only those supported formatting modes. Test in isolation:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_datetime.c engine/ft5955_compat_locale.c \\
      tests/test_moh_compat_datetime.c \\
      -o /tmp/ft5955_compat_datetime_test
    /tmp/ft5955_compat_datetime_test

The time, FLS and locale compatibility C test binaries passed on the Nobara host;
the locale test and updated complete loader must still be checked there.
the complete PE loader smoke-test must still be built and checked on Nobara.

An optional *build-only* command exists:

    bash tools/build_moh_engine_smoke.sh

This builds native/build/ft5955_moh_smoke but never loads a proprietary DLL.
**Do not execute the smoke binary yet on the live workstation.**

## Next work on this branch

1. Implement the missing Windows shims with actual expected semantics, not
   blanket success or unbounded access to the host registry/filesystem.
2. Validate PE header bounds/mapping and the remaining FT9201 shims against
   the exact known DLL. Missing-import names alone are not enough.
3. Trace the MOH WinBio engine ABI, pipeline/storage layout and BIR requirements
   before using Attach or accepting any sample.
4. Execute a query-interface-only smoke-test in a disposable, isolated process
   with a trusted DLL and no USB, initially using synthetic data.
5. Validate real-image quality, multiple-impression enrolment, withheld genuine
   verification and different-finger rejection privately.
6. Only then integrate into an isolated libfprint FpDevice test build. Keep
   system fprintd/PAM untouched until independently validated.

A long-term fully native matcher may then be developed against the validated
vendor engine as a reference.
