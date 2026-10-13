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
- **Expected after this patch: 92/110 names covered, 18 still missing**.
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

Its expected current result is **92/110 covered, 18 missing** and exit status 1.
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

GetTempPathW is the first filesystem-adjacent shim. It reports a
**synthetic Windows path** (C:\\Windows\\Temp\\) and honours the Win32
buffer-size contract, but it does **not** map that path onto Linux or permit
filesystem writes. The inherited CreateFileW remains a failure-only shim.
Test it offline:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_temp.c tests/test_moh_compat_temp.c \\
      -o /tmp/ft5955_compat_temp_test
    /tmp/ft5955_compat_temp_test

**Additional safeguard:** even if import-name coverage eventually reaches
110/110, the default ft_engine_smoke_interface entry point is now blocked
unless the source is deliberately built with
FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT. Do NOT use that compile-time option
until the inherited FT9201 shims, PE bounds and the 5955 WinBio ABI have
been reviewed. The 5955-specific Attach path remains separately disabled.

CompareStringW now has a bounded *experimental* ASCII-only implementation
with Windows-x64 ABI, Win32 return values (1/2/3, error 0), a 4096-code-unit
cap, and support for en-GB/en-US/invariant + flags 0/NORM_IGNORECASE.
**It is not equivalent to Windows NLS linguistic collation**: exact order and
equivalence for punctuation, case, locale-specific characters and unhandled
options cannot be inferred from ASCII comparisons alone. Unsupported
characters/flags/locales fail closed, and the real MOH DLL must not be run
until its CompareStringW use has been reviewed against Windows behavior.

Synthetic, offline test:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_compare.c engine/ft5955_compat_locale.c \\
      tests/test_moh_compat_compare.c -o /tmp/ft5955_compat_compare_test
    /tmp/ft5955_compat_compare_test

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

**Important:** 92/110 means **registered API names**, not 83 APIs fully
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

## Existing-shim correctness audit: per-thread Win32 TLS

The FT9201 baseline used a process-global array for all four Win32 TLS
functions. `TlsAlloc` allocated monotonically increasing slot numbers,
`TlsFree` never actually freed a slot and separate pthreads could read each
other's TLS values. This is unsafe for native WinBio matcher execution.

`engine/ft5955_compat_tls.[ch]` now implements:

- `TlsAlloc`: global bounded slot pool (1,088 Win32-style indices).
- `TlsGetValue` / `TlsSetValue`: values scoped to the current Linux
  thread using pthread TLS, including genuine NULL as a successful result.
- `TlsFree`: releases the global index; incrementing its generation on
  reuse prevents stale values in other threads being exposed.
- Invalid indices report Win32 `ERROR_INVALID_PARAMETER` (87) via the
  now thread-local `GetLastError`; allocating beyond capacity reports
  an error and `TLS_OUT_OF_INDEXES`.

Thread storage is freed when the pthread exits. Unlike FLS, TLS has no
destructor callbacks for individual indices. Synthetic tests cover three
concurrent threads, slot reuse while other threads hold previous values,
invalid indices and exhaustion of the bounded index pool.

    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_tls.c engine/ft5955_compat_error.c \\
      tests/test_moh_compat_tls.c -o /tmp/ft5955_tls_test
    /tmp/ft5955_tls_test
    bash tools/build_moh_engine_smoke.sh

**Name coverage remains 86/110 (24 missing).** This fixes four existing
registered shims, not four new imports. The vendor engine's direct TEB,
CRT TLS, fiber and thread-creation behaviour is not yet verified; real DLL
execution stays blocked.

## Existing-shim correctness audit: per-thread GetLastError

The FT9201 baseline stored its Windows `GetLastError` value in a **single
global variable**, so errors from simultaneous matcher threads could
overwrite one another. We replaced the Win32 ABI `GetLastError` and
`SetLastError` entry points with C11 `_Thread_local` storage in
`engine/ft5955_compat_error.[ch]`. The existing `TlsGetValue` success
path resets **only the current thread's** last-error value; the
failure-only `CreateFileW` placeholder sets the current thread's
ERROR_FILE_NOT_FOUND (2) value.

These changes do **not** add any new imports: expected registered coverage
remains **86/110**, with 24 absent. The multi-threaded test isolates two
worker threads and checks that neither can overwrite the other or the main
thread:

    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_error.c tests/test_moh_compat_error.c \\
      -o /tmp/ft5955_error_test
    /tmp/ft5955_error_test
    bash tools/build_moh_engine_smoke.sh

The test was compiled and executed in the development sandbox; the full
loader build must also be checked on Nobara. As with the critical-section
bridge, this implements the **imported API behaviour**, not full
Windows TEB emulation: code that reads `NtCurrentTeb()->LastErrorValue`
directly would still need compatible per-thread TEB state. The imported Win32 TLS calls now use per-thread storage (see the section
above), but the synthetic Windows TEB and CRT TLS layout still require
verification. **Do not enable Windows DLL execution yet.**

## Existing-shim correctness audit: Win32 CRITICAL_SECTION

The borrowed FT9201 loader's **five critical-section entries were no-ops**.
That is unsafe for a potentially multithreaded matcher: imports appear
'covered' even though actual mutual exclusion is absent.

A new x86-64 Windows-ABI wrapper in
`engine/ft5955_compat_cs.c` backs these calls with **recursive pthread
mutexes** keyed by the CRITICAL_SECTION address:

- InitializeCriticalSection
- InitializeCriticalSectionAndSpinCount
- EnterCriticalSection
- LeaveCriticalSection
- DeleteCriticalSection

The wrappers preserve recursion, prevent simultaneous access, allow
Delete/reinitialise and pin active users across concurrent Delete.
Invalid API use aborts in the isolated experiment instead of silently
ignoring locking. This is **not yet ABI-complete**: it does not reproduce
the in-memory Windows CRITICAL_SECTION fields, so direct reads of
`LockCount`, `OwningThread` or `DebugInfo` by the MOH engine must be
ruled out before enabling execution. Deleting a lock while held by the
calling thread is invalid and can deadlock. Do not use in production
until these limitations are resolved.

Test the C implementation without a DLL or USB:

    cc -std=gnu11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_cs.c tests/test_moh_compat_cs.c \\
      -o /tmp/ft5955_cs_test
    /tmp/ft5955_cs_test

This tests recursive acquisition, 4 concurrent threads performing
120,000 guarded increments, absence of overlapping critical sections,
and safe reuse after Delete. **Import-name coverage stays 86/110**:
the change improves five previously registered but ineffective shims.
Neither Windows DLL entry points nor libfprint/PAM are executed or modified.

## Current offline TEB audit and guarded loader integration

The SHA-pinned GS/FS scanner and instruction-context tool (documented in
[moh-teb-static-audit.md](moh-teb-static-audit.md)) found indirect accesses
to thread stack limits/base, PEB.NtGlobalFlag and process-parameter flags.
The original pinned MOH DLL has **no PE TLS directory**; its imported
Win32 TLS APIs may still be used.

The still-blocked loader now uses per-thread TEB/PEB scaffolding with
actual pthread stack bounds, prepares GS before `DllMain`, and rejects
any unexpected PE TLS directory without calling vendor TLS callbacks.
It no longer uses the old process-global dummy TEB and fake stack.
The 5955 DLL has **not** been executed; Windows API semantics, stack
probe behaviour, PEB values, PE file bounds and ABI are still unaudited.
Static analysis and standalone tests cannot establish runtime safety.

## PE input validation (offline, DLL execution still locked)

The original FT9201 loader read `e_lfanew`, image size, section offsets
and section bytes without first validating their on-disk ranges. The
5955 bridge now checks PE32+ x64 headers, a bounded section table,
file-backed section data, section/image-page overlap, W+X section
permissions, entry point location, required import-directory coverage
and the absence of a TLS directory **before** copying PE sections or
attempting to map executable memory. A complete regular-file read is
required; truncated, oversized, non-regular and symlink paths fail
closed. Its import descriptor/thunk/name parsing is bounded within
the scratch image and the import directory's declared size.

Synthetic C tests:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_pe_guard.c tests/test_moh_pe_guard.c \\
      -o /tmp/ft5955_pe_guard_test
    /tmp/ft5955_pe_guard_test

Also check the **actual SHA-verified original DLL** without loading it:

    python3 tools/moh_pe_guard_probe.py '/home/tim/Downloads/7_Fingerprint-module.zip'
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh

The private-DLL probe compiles an inert C validator into a temporary
directory, verifies the original MOH SHA256, checks the image structure
and removes the extracted DLL and helper afterwards. It neither
loads executable DLL code nor accesses USB/fingerprints.

**Bounded export lookup:** the original FT9201 export resolver trusted
the DLL's name, ordinal and function tables without verifying their
ranges. `ft5955_pe_find_export` now checks export-directory limits,
array sizes, function/name RVAs, string terminators and ordinals, and
rejects forwarded exports (not callable functions). The guarded loader
additionally requires the returned RVA to lie inside a section marked
executable. The SHA-pinned, read-only probe reconstructs the image in
non-executable heap memory and checks the real MOH
`WbioQueryEngineInterface` export.

Synthetic export test:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_pe_exports.c tests/test_moh_pe_exports.c \\
      -o /tmp/ft5955_pe_exports_test
    /tmp/ft5955_pe_exports_test

Re-run the **private original DLL** metadata probe to verify this export
on Nobara; it never executes the DLL:

    python3 tools/moh_pe_guard_probe.py '/home/tim/Downloads/7_Fingerprint-module.zip'
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh

**Important limitations:** header, section, import and export checks are
still only partial PE safety checks. Loaded-image permissions/lifetime,
relocation assumptions, failure-path resource cleanup and Windows ABI/shim
correctness require separate review. Passing this test is **not** authorisation
to enable vendor DLL execution or to integrate with system
fprintd/PAM. Registered import names remain **86/110, 24 missing**.

## Existing-shim correctness: Windows thread and process IDs

The FT9201 loader previously returned fixed numerical IDs
`1234` (process) and `5678` (thread), even when called from
different Linux threads. The new `GetCurrentProcessId` and
`GetCurrentThreadId` shims use Linux's real process and thread
identifiers, returned with the Windows x64 calling convention.
The experimental per-pthread TEB fixture also stores those same
64-bit integer values in `TEB.ClientId.UniqueProcess` (+0x40)
and `TEB.ClientId.UniqueThread` (+0x48). They are synthetic
numeric identities, **not Windows kernel handles**.

The offline test checks three live pthreads against their own
TEB data, with stable IDs within each thread and distinct IDs
across threads. Neither the native kernel thread IDs nor their
TEB fields are biometric information.

    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_identity.c \\
      engine/ft5955_compat_teb_layout.c \\
      tests/test_moh_compat_identity.c -o /tmp/ft5955_identity_test
    /tmp/ft5955_identity_test
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh

The new shim replaces two **already registered** import names.
Expected coverage remains **86/110, 24 missing**. TEB state
beyond these fields, Windows handle semantics and cross-thread
engine behaviour still require validation. Do not execute the
vendor DLL.

## Existing-shim correctness: tracked Win32 process heap

The inherited FT9201 heap shims returned a sentinel process-heap handle,
freed arbitrary pointers directly with `free`, reported all block sizes
as zero and treated every heap validation as successful. These behaviours
could cause memory corruption or failed memory-management checks during
engine initialisation.

`engine/ft5955_compat_heap.[ch]` now provides a restricted process-only
heap with a stable opaque handle, mutex-protected allocation metadata,
16-byte-aligned allocations, actual requested sizes, `HEAP_ZERO_MEMORY`
for allocations and growth, and tracked `HeapFree`/`HeapReAlloc`.
Unknown, freed or foreign pointers are rejected instead of being passed
to the host allocator. `HeapValidate` verifies membership in this
tracked allocation set but **does not inspect heap metadata for
corruption**. `HeapQueryInformation` supports only
`HeapCompatibilityInformation` for the synthetic standard heap.

Deliberately unsupported: private heap handles, Windows heap exception
generation, `HEAP_NO_SERIALIZE` (not valid for our process heap),
low-fragmentation heap modes and full Windows heap diagnostics. The
`HEAP_REALLOC_IN_PLACE_ONLY` subset can resize within existing capacity
but will fail growth that would require moving a pointer. Unsupported
flags fail rather than claim success.

The standalone test exercises zero-fill and alignment, resizing, buffer
preservation, invalid/double-freed pointers, thread-local error handling,
the limited query, and 12,000 allocation/free operations across four
concurrent pthreads. It never executes the proprietary DLL.

    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_heap.c engine/ft5955_compat_error.c \\
      tests/test_moh_compat_heap.c -o /tmp/ft5955_heap_test
    /tmp/ft5955_heap_test
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh

All seven functions replace **already registered shims**, so expected
name coverage stays **86/110 (24 missing)**. Passing these synthetic
tests does not establish engine readiness or Windows heap equivalence;
the DLL remains locked out.

## Existing-shim correctness: real Windows clock semantics

The borrowed FT9201 loader returned artificial timestamps:
`GetSystemTimeAsFileTime` added a fixed count on each call regardless
of the actual UTC time, while `GetTickCount` advanced exactly five
milliseconds per invocation. Neither modelled Windows timing and both
could interfere with timeouts or timestamp checks.

The registered shims now use Linux clocks, without accessing any USB
device, fingerprint information or Windows executable:

- `GetSystemTimeAsFileTime` reads `CLOCK_REALTIME` and converts from
  the Unix epoch to 100-nanosecond intervals since 1 January 1601 UTC.
  The 8-byte result matches the x64 FILETIME two-DWORD representation.
- `GetTickCount` reads `CLOCK_BOOTTIME`, converts to milliseconds and
  deliberately truncates to the Windows 32-bit wrapping counter.
  `CLOCK_BOOTTIME` includes suspended time on Linux.
- Existing `QueryPerformanceCounter` uses `CLOCK_MONOTONIC`; its
  independent high-resolution counter is not treated as wall time.

Standalone Nobara test:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_time.c tests/test_moh_compat_wallclock.c \\
      -o /tmp/ft5955_wallclock_test
    /tmp/ft5955_wallclock_test
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh

The test compares the UTC FILETIME with `CLOCK_REALTIME` before/after
the call and the tick count with `CLOCK_BOOTTIME` before/after, including
the wrap-safe unsigned difference after a brief sleep. System clock
adjustments during the test could cause a false negative. If the native
clock read fails, the narrow shim returns zero: this is an unsupported
clock-failure case, not a complete Windows error-path emulation.

These replace **two existing registered imports**: coverage remains
**86/110 names, 24 missing**. The Windows DLL is still locked out.

## Existing-shim correctness: fixed Windows x64 SYSTEM_INFO buffer overrun

The inherited FT9201 `GetSystemInfo` handler called `memset(p,0,64)`.
Microsoft's Windows **x64 SYSTEM_INFO structure is 48 bytes**, not 64.
A caller allocating the correct 48-byte object could therefore have
16 bytes of adjacent stack/heap memory overwritten.

`engine/ft5955_compat_sysinfo.[ch]` now defines the exact 48-byte
Win64 layout with compile-time size and field-offset assertions.
`GetSystemInfo` writes exactly 48 bytes. It reports:

- x64 architecture (9), processor type (8664) and CPU family/revision
  from CPUID leaf 1, where available.
- The native page size from `sysconf(_SC_PAGESIZE)`.
- The number of online logical processors, capped to a synthetic Windows
  processor group of at most 64, and a matching group-relative mask.
- Windows' 64 KiB allocation granularity and a representative x64
  userspace application address range.

**Limitations:** the processor group/mask is synthetic and may not
match Linux affinity or actual Windows CPU-group assignment; the
address range does not guarantee a corresponding Linux mapping.
The shim does not implement Windows `VirtualAlloc` or physical
processor topology. This is a safe compatibility subset, not a complete
OS model. It does not access USB/biometric data or load a PE image.

The test places 16-byte sentinels immediately before and after the
48-byte structure and validates host-derived fields and multiple calls
without aborting on failure:

    cc -std=c11 -O2 -Wall -Wextra -Werror -Iengine \\
      engine/ft5955_compat_sysinfo.c tests/test_moh_compat_sysinfo.c \\
      -o /tmp/ft5955_sysinfo_test
    /tmp/ft5955_sysinfo_test
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh

Windows API reference:
https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/ns-sysinfoapi-system_info

This replaces **one existing registered import**. Expected coverage
remains **86/110, 24 missing**, and Windows DLL execution is still
disabled.

## New import: virtual Windows environment, no Linux environment changes

A Windows `SetEnvironmentVariableW` shim now writes only to a bounded,
in-process **virtual Windows environment**. It never calls
`setenv`, `putenv`, changes Linux `environ`, or writes host files.
`GetEnvironmentStringsW` and `FreeEnvironmentStringsW` replace the
inherited FT9201 empty, static buffer and no-op free:

- Each `GetEnvironmentStringsW` call returns a separate, UTF-16,
  double-NUL-terminated snapshot, sorted case-insensitively by ASCII
  name; the caller must release it through `FreeEnvironmentStringsW`.
- Mutations do not alter previous snapshots; unknown and double-freed
  snapshot pointers are rejected without invoking `free` on them.
- `SetEnvironmentVariableW` updates names case-insensitively, permits
  empty values and deletes a name only when the value pointer is NULL.
- A pthread mutex serialises updates and snapshots across threads.
  Inputs are limited to 64 variables, 127-character names and 4,096-
  character values, with printable ASCII UTF-16 only. Unsupported
  Unicode, Windows drive-current-directory pseudo-variables and
  unbounded process environments are intentionally rejected.
- The environment initially starts **empty**, and neither the synthetic
  PEB's `ProcessParameters.Environment` pointer nor an imported
  `GetEnvironmentVariableW` shim is implemented yet. A real Windows
  engine may need these; name coverage is not execution readiness.

Synthetic test (no Windows DLL, USB, biometric samples or host updates):

    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_env.c engine/ft5955_compat_error.c \\
      tests/test_moh_compat_env.c -o /tmp/ft5955_env_test
    /tmp/ft5955_env_test
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh
    python3 tools/moh_engine_preflight.py '/home/tim/Downloads/7_Fingerprint-module.zip'

The tests cover snapshots, update/deletion, ASCII case-insensitive
names, invalid arguments, Linux `getenv` isolation and four concurrent
writer threads. Imported name coverage is **expected** to improve to
**87/110 (23 missing)**, pending the user's real-DLL static preflight.
Nothing changes the DLL-execution gates.

Windows API references:
https://learn.microsoft.com/en-us/windows/win32/api/processenv/nf-processenv-setenvironmentvariablew
https://learn.microsoft.com/en-us/windows/win32/api/processenv/nf-processenv-getenvironmentstringsw

## x64 SLIST compatibility: one new import and two repaired shims

The inherited FT9201 loader's `InitializeSListHead` merely cleared a
16-byte header, while `InterlockedFlushSList` always returned NULL and
discarded any potential list. The verified MOH DLL additionally imports
`InterlockedPushEntrySList`, which was unresolved.

The experimental bridge now uses a 16-byte-aligned Win64 header and
`SLIST_ENTRY` with an atomic, 128-bit compare-and-exchange loop.
It stores the x64 Depth (16 bits), Sequence (48 bits) and aligned
NextEntry pointer. The push operation links the new entry to the
former first entry and returns that **previous first entry**. Flush
atomically removes and returns the entire linked list. Concurrent
pushes and flushes update the header as one operation, rather than
mutating it through non-atomic pointer writes.

This is intentionally limited to this pinned x64 environment:
- Headers and entries must be 16-byte aligned and initialised before use.
- No `InterlockedPopEntrySList` (not imported by the verified DLL);
  no safe reclamation if callers free entries concurrently with list use.
- The code follows a documented x64 16-byte header representation but
  has not been proven binary-compatible with every modern Windows header
  variant or every CRT use of its fields.
- The test exercises direct header fields, push return pointers, empty
  and populated flush, list traversal and 6,000 entries pushed by four
  pthreads. It never executes the original Windows DLL.
- GCC's 128-bit atomic operations require `-latomic` for the Linux
  build; this was added to the **still-gated** smoke build.

Offline Nobara tests:

    cc -std=gnu11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_slist.c tests/test_moh_compat_slist.c \\
      -latomic -o /tmp/ft5955_slist_test
    /tmp/ft5955_slist_test
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh
    python3 tools/moh_engine_preflight.py '/home/tim/Downloads/7_Fingerprint-module.zip'

**Expected import-name coverage: 88/110, 22 missing**, not yet
validated on Nobara. This is one previously unresolved name plus two
repaired existing functions; it is not proof that Windows SList
behaviour is complete. DLL execution remains blocked.

Microsoft Win32 references:
https://learn.microsoft.com/en-us/windows/win32/api/interlockedapi/nf-interlockedapi-interlockedpushentryslist
https://learn.microsoft.com/en-us/windows/win32/api/interlockedapi/nf-interlockedapi-initializeslisthead
https://learn.microsoft.com/en-us/windows/win32/sync/interlocked-singly-linked-lists

## Four new ADVAPI32 imports: private ANSI registry

The verified MOH DLL imports `RegOpenKeyExA`, `RegQueryValueExA`,
`RegCloseKey` and `RegSetKeyValueA`. The guarded loader now registers a
small **in-memory-only** implementation of all four in
`engine/ft5955_compat_registry.[ch]`. This does **not** access actual
Windows registry hives, Nobara configuration files, or user settings.

- Predefined HKCU/HKLM (and other basic non-performance predefined roots)
  are recognised as synthetic registry roots. Initially there are no keys
  or values. `RegOpenKeyExA` never creates a missing key;
  `RegSetKeyValueA` creates an in-memory key and required path prefixes.
- Newly opened keys use generation-tagged, opaque 64-bit handles. Closing
  invalidates the handle; unknown or previously closed handles return
  `ERROR_INVALID_HANDLE` rather than being dereferenced or freed.
- Keys and value names compare case-insensitively for printable ASCII.
  `RegSetKeyValueA` supports bounded `REG_SZ`, `REG_BINARY` and
  `REG_DWORD` values; UTF-8/Windows ANSI code page conversion, full
  registry types, ACLs, WOW64 views, dynamic notifications and remote
  registry connections are **not** implemented.
- `RegQueryValueExA` returns the size/type for a value, and reports
  `ERROR_MORE_DATA` with the required byte length for short buffers.
  Handles opened with insufficient rights return `ERROR_ACCESS_DENIED`.
- Memory-only storage is limited to 128 keys, 256 values (4,096 bytes
  each), 128 open handles and 255-byte normalised paths. One pthread
  mutex serialises all operations. It is not persistent.

Synthetic regression test: missing keys, nested key creation, case-
insensitive readback, binary-size contract, short buffers, access rights,
closed handles, invalid arguments and four concurrent reader/writers.

    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_registry.c tests/test_moh_compat_registry.c \\
      -o /tmp/ft5955_registry_test
    /tmp/ft5955_registry_test
    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    bash tools/build_moh_engine_smoke.sh
    python3 tools/moh_engine_preflight.py '/home/tim/Downloads/7_Fingerprint-module.zip'

This adds four formerly unresolved names; **expected coverage: 92/110,
18 missing**, pending Nobara confirmation. It does not establish matching
engine readiness: the actual Windows registry's FocalTech installation
settings, if required by the DLL, will need separate examination and
careful synthetic equivalents. DLL execution and libfprint/PAM remain
unchanged and blocked.

References:
https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regopenkeyexa
https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regqueryvalueexa
https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regsetkeyvaluea

## Next work on this branch

1. Implement the missing Windows shims with actual expected semantics, not
   blanket success or unbounded access to the host registry/filesystem.
2. Complete the PE export/import-directory, relocation, mmap and
   failure-cleanup audits, plus the remaining inherited FT9201 shims,
   against the exact known DLL. Bounded header parsing is only a first step.
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
