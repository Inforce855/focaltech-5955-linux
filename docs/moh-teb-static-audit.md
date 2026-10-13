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
