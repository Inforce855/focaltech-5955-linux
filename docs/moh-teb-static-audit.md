# FocalTech 5955 MOH — offline x64 TEB access audit

This is a **static analysis** of the *actual private 2808:5955 MOH*
`ftWbioEngineAdapter.dll`; it neither executes that DLL nor accesses
the fingerprint reader, images, templates, libfprint or PAM.

## Why this matters

The inherited FT9201 loader originally used one process-global dummy
TEB/PEB for every thread and invoked PE TLS callbacks before installing
GS. Offline inspection of the pinned 5955 MOH DLL showed **no PE TLS
directory**, and synthetic tests validated a per-thread TEB/PEB fixture.

The still-disabled loader now prepares that per-thread fixture and installs
GS before DllMain; it **rejects any PE image with a TLS directory**, instead
of invoking callbacks. This is a compatibility improvement, **not permission
to execute the DLL**.

Remaining issues:

- TEB+0x68 (LastErrorValue) is not synchronized with the per-thread
  `GetLastError` function shim.
- TEB+0x58 is a synthetic CRT static-TLS pointer, distinct from the Win32
  `TlsAlloc` index mapping. The pinned DLL has no static TLS directory,
  but its CRT and potential direct TEB access remain unverified.
- `arch_prctl(ARCH_SET_GS,...)` affects only the calling thread; all DLL
  threads must be provisioned and safe thread creation remains unaudited.
- The fixture uses actual pthread stack bounds, not Windows stack growth
  or Windows guard-page semantics. The pinned DLL includes stack probes.
- The PEB values observed in static code are partial placeholders, not a
  full Windows environment.
- The inherited PE file/section parser and many other registered Win32
  shims still require boundary and semantic audits.

None of these are proof of runtime reachability, correctness or safety.

## Safe first test on the actual original archive

    cd ~/Projects/focaltech-5955-moh-test
    git fetch origin
    git switch --detach origin/feature/ft5955-moh-engine-bridge
    python3 -m unittest discover -s tests -p 'test_moh_teb_audit.py'
    python3 tools/moh_teb_audit.py '/home/tim/Downloads/7_Fingerprint-module.zip'

The tool checks the exact SHA256 of the known MOH DLL, extracts the DLL
temporarily with private permissions, streams `objdump -d -M intel`,
and prints only instruction addresses, counts and likely TEB offsets.
The temporary DLL is deleted. It does not save or upload disassembly.
No `sudo`, USB or fingerprints are needed.

Do **not** publish the original proprietary DLL, disassembled machine
code, real fingerprint images or templates. The short, address-only
summary is sufficient for our next decision.

## Follow-up: focused instruction windows around the eight GS accesses

The actual pinned DLL yielded **eight direct GS segment references**:

- Seven at `GS:0x30` (TEB.Self, commonly obtaining the TEB pointer).
- One at `GS:0x10` (NT_TIB.StackLimit).
- No direct `GS:0x68` or `GS:0x58` references were observed.

That does not rule out indirect TEB reads through a pointer returned by
`GS:0x30`. The next private, read-only test shows a few instructions before
and after each reference; the snippets can be inspected for expressions
such as `[rax+0x68]` or `[rcx+0x58]`. **Those expressions do not prove TEB
access on their own**: register provenance and overwrites must be traced.

    cd ~/Projects/focaltech-5955-moh-test
    git fetch origin
    git switch --detach origin/feature/ft5955-moh-engine-bridge
    python3 -m unittest discover -s tests -p 'test_moh_teb_context.py'
    python3 tools/moh_teb_context.py '/home/tim/Downloads/7_Fingerprint-module.zip'

The new tool re-verifies the DLL SHA256 and streams `objdump` output.
It does not write the instructions to disk; it prints up to 16 short local
contexts (default: 3 preceding + 9 following instructions) for static
inspection. Keep private disassembly snippets out of the public repo; share
only what is needed to decide TEB-field requirements. No vendor code is
executed.

## Focused MOH observations (13 October 2026)

The user ran the pinned DLL context inspector against the actual MOH binary;
all four synthetic parser tests passed. Inspection revealed:

| Instruction | Verified static behaviour | Implication |
| --- | --- | --- |
| 0x18012e691 | `gs:0x30` -> `[TEB+0x08]` | Reads real StackBase, not dummy TEB buffer |
| 0x18013566f, 0x1801356aa, 0x1801356f4 | `gs:0x30` -> StackLimit/StackBase | Stack bounds feed range checks ending in `int 0x29` |
| 0x18018d750 | `gs:0x30` -> `[TEB+0x60]` -> `[PEB+0xbc]` | Reads PEB.NtGlobalFlag (exact bit use needs verification) |
| 0x18018d76c | `gs:0x30` -> `[TEB+0x60]` -> `[PEB+0x20]` -> `[ProcessParameters+0x08]` | Reads RTL_USER_PROCESS_PARAMETERS.Flags |
| 0x1801a5b6c | `gs:0x10` -> stack-page probing | Must supply real thread stack bounds, not arbitrary addresses |

These are **static code paths**, not verified runtime reachability.
The supplied instructions also show that the 5955 matcher does read TEB
stack and PEB fields **indirectly**, even though the earlier scanner saw
only direct GS:0x30 and GS:0x10 references.

### Safe, isolated layout prototype

`engine/ft5955_compat_teb_layout.[ch]` implements a **non-executing**
per-pthread TEB layout prototype. It uses `pthread_getattr_np` and
`pthread_attr_getstack` to obtain the calling thread's actual stack
region and checks that a local stack variable falls within those bounds.
Each pthread gets a private TEB, CRT TLS array and CRT TLS buffer. A
process-wide synthetic PEB has `ProcessParameters` at +0x20 and
`NtGlobalFlag` at +0xbc, and the referenced parameters block provides
`Flags` at +0x08.

The initial flag values (0 for NtGlobalFlag, 1 for normalized parameters)
are experimental placeholders based on known Windows structure layouts,
**not validated values for the target engine**. Linux stack bounds do not
provide Windows stack expansion or guard-page semantics. Actual module
execution, vendor TLS callbacks, process launch and USB all
remain disabled; the still-gated loader now prepares GS before DllMain.

Run the synthetic three-thread test on Nobara:

    cd ~/Projects/focaltech-5955-moh-test
    git fetch origin
    git switch --detach origin/feature/ft5955-moh-engine-bridge
    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_teb_layout.c tests/test_moh_compat_teb_layout.c \\
      -o /tmp/ft5955_teb_layout_test
    /tmp/ft5955_teb_layout_test

The test asserts distinct TEB and CRT TLS buffer addresses for three
concurrent threads; valid native stack bounds; TEB self-reference;
shared PEB and parameters pointers; and the tested fixture field values.
It never sets the GS register and does not execute or load a PE DLL.

The prototype is now **wired into the disabled loader path**, but has
not been exercised with the MOH DLL. Its stack bounds, PEB data,
unimplemented Win32 shims and Windows ABI still need independent review
before any sandboxed `WbioQueryEngineInterface` call.

## Offline PE32+ TLS callback metadata check

The **original FT9201** PE loader copied the static TLS template and ran
TLS callbacks before installing the synthetic x64 TEB in GS.
The pinned 5955 MOH engine's PE TLS preflight returned **no TLS directory**.
The experimental loader now rejects any unexpected TLS directory; the
callback runner has been removed from that path.

The new `tools/moh_tls_preflight.py` reads these structures without
loading or executing the DLL. It verifies the SHA256 of the original
private MOH DLL, bounds-checks the PE32+ headers, data directories,
sections and callback pointer array, and displays callback **addresses
only**, not executable disassembly. The original archive is extracted
into a private, automatically deleted temporary directory.

    cd ~/Projects/focaltech-5955-moh-test
    git fetch origin
    git switch --detach origin/feature/ft5955-moh-engine-bridge
    python3 -m unittest discover -s tests -p 'test_moh_tls_preflight.py'
    python3 tools/moh_tls_preflight.py '/home/tim/Downloads/7_Fingerprint-module.zip'

The synthetic tests build minimal PE32+ fixtures including two callbacks,
an empty callback table, absent TLS, truncated PE data, invalid
index/callback addresses and a nonterminated callback list. They do
**not** use or print real biometric samples or vendor DLL bytes.

Per Microsoft's PE format specification, the TLS directory stores
VAs (not RVAs) for raw template bounds, index pointer and the
NULL-terminated callback pointer array:

https://learn.microsoft.com/en-us/windows/win32/debug/pe-format#the-tls-section

The **absence of a TLS directory** does **not** imply the Windows CRT
avoids imported Win32 TLS, TEB or PEB access. Static metadata does not
establish reachability. Windows DLL execution and fprintd/PAM integration
remain disabled.

## Experimental loader wiring — still blocked

After the no-TLS result, `engine/ft_engine.c` now uses
`ft5955_teb_prepare_current` and `ft5955_teb_view_current` in its
still-locked PE initialisation path. It installs the caller's private GS
TEB before the first vendor `DllMain` call. It rejects any PE TLS
directory and cannot execute callbacks. Repeated entry on the same
thread preserves its TEB/CRT TLS data; other threads require their own
layout and GS installation.

**Normal builds do not execute the Windows DLL.** The legacy Attach
entry now additionally requires **both** deliberate compile-time unlocks,
not merely its original Attach-specific one. Neither unlock should be
enabled at this stage. The SHA-pinned import check still reports
86 of 110 names covered and 24 missing. The loader's
PE bounds, process flags, thread/TEB restoration, Windows API shims and
WinBio ABI must all be reviewed before any explicit execution unlock.

Safe regression checks (no proprietary DLL execution):

    python3 -m unittest discover -s tests -p 'test_moh_loader_teb_gate.py'
    cc -std=c11 -O2 -Wall -Wextra -Werror -pthread -Iengine \\
      engine/ft5955_compat_teb_layout.c tests/test_moh_compat_teb_layout.c \\
      -o /tmp/ft5955_teb_layout_test
    /tmp/ft5955_teb_layout_test
    bash tools/build_moh_engine_smoke.sh

## What the report means

Examples of common x64 GS/TEB offsets:

| GS offset | Widely documented x64 TEB interpretation |
| --- | --- |
| 0x30 | NT_TIB.Self — pointer to TEB |
| 0x40 / 0x48 | CLIENT_ID — process / thread ID |
| 0x58 | ThreadLocalStoragePointer |
| 0x60 | ProcessEnvironmentBlock (PEB) |
| 0x68 | LastErrorValue |
| 0x1480 | TlsSlots (common x64 layout) |

The tool distinguishes constant `gs:0x68` from computed
`gs:[rax+0x68]` (labeled **dynamic**). It also reports FS segment
references separately.

A direct `gs:0x30` access may obtain the TEB pointer and then read
other fields through ordinary instructions, **which this script does
not follow**. This is a deliberately limited triage, not full
data-flow analysis. If the DLL has no direct GS references, it still
does not prove the DLL avoids the TEB, nor that inherited FT9201 shims
are correct.

References:
- Microsoft TEB structure (unstable internal structure):
  https://learn.microsoft.com/en-us/windows/win32/api/winternl/ns-winternl-teb
- Technical offset study:
  https://www.geoffchappell.com/studies/windows/win32/ntdll/structs/teb.htm

The DLL-execution and unsupported-import guards remain active.
Registered import names remain **86/110**, with **24** absent.
