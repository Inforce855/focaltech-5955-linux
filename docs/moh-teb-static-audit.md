# FocalTech 5955 MOH — offline x64 TEB access audit

This is a **static analysis** of the *actual private 2808:5955 MOH*
`ftWbioEngineAdapter.dll`; it neither executes that DLL nor accesses
the fingerprint reader, images, templates, libfprint or PAM.

## Why this matters

The imported FT9201 loader installs a synthetic TEB at the Linux x64 GS
base, but the loader's `g_teb`, `g_tls_array` and `g_tls_block` are
currently process-global objects, not per-thread state. The newer
`GetLastError` and `TlsGetValue` *function* shims use per-thread
storage, but any direct Windows x64 TEB access through `gs:` may still
see stale/shared state.

Other gaps in the current loader:

- `g_teb+0x68` (TEB.LastErrorValue) is not synchronized with the new
  per-thread `GetLastError` shim.
- `g_teb+0x58` points to the inherited global CRT TLS array, not the
  new Win32 `TlsAlloc` slot map.
- The inherited loader runs PE TLS callbacks **before** it installs its
  synthetic GS TEB, which may make initialization unsafe.
- `arch_prctl(ARCH_SET_GS,...)` changes the calling thread only.
  Thread creation and direct TEB access must be audited separately.
- `g_teb+0x08` contains a dummy stack base. Its safety is unverified.

These are source-level concerns, not proof that the engine uses any of
these paths during normal authentication.

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
execution, GS installation, TLS callbacks, process launch and USB all
remain disabled.

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

**Do not wire this prototype into engine execution yet.** Its stack
bounds and the PEB data must be evaluated alongside Windows stack probes,
PE TLS callback ordering and ABI expectations before any sandboxed
`WbioQueryEngineInterface` call.

## Offline PE32+ TLS callback metadata check

The old PE loader currently prepares the DLL's static TLS template and
invokes its TLS callbacks **before** installing a synthetic x64 TEB in GS.
We should not change the execution sequence blindly: first inspect the
actual DLL's TLS directory to establish its template size, static TLS
index and callback list.

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

A callback count of zero does **not** imply the Windows CRT avoids
TEB/PEB access, and a positive count does **not** prove a particular
callback executes any of the TEB instructions we found. This is
metadata triage, not reachability analysis. The compiled MOH executable
and system fprintd/PAM integrations remain disabled.

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
