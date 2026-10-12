# Compare the Windows and Linux fingerprint images (VM experiment)

The working Windows VirtualBox guest successfully authenticates an enrolled finger on the physical **2808:5955** reader. The previous host-side `usbmon` runs established that the optional sensor-image AES flag is **0** and that Windows receives one **10,246-byte framed image** per successful authentication.

The next question is whether Windows' **processed image** looks substantially different from our unsigned/signed 16-bit normalisers. Windows Biometric Framework (WBF) has an **official** sample API. We should attempt this before debugging or modifying `FtWbioDriverUmdfV3.dll`.

## First step: test whether WBF allows an intermediate sample

Source: `tools/windows_winbio_sample_probe.ps1`.

From the **Windows VM itself**, open **Windows PowerShell (Run as administrator)** and execute:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Inforce855/focaltech-5955-linux/main/tools/windows_winbio_sample_probe.ps1" -OutFile "$env:TEMP\windows_winbio_sample_probe.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\windows_winbio_sample_probe.ps1"
```

The script compiles a tiny C# P/Invoke wrapper *locally* using PowerShell's built-in `Add-Type`; it downloads no binary and installs nothing. It opens a `WINBIO_POOL_SYSTEM` session with `WINBIO_FLAG_RAW` and requests **one** `WINBIO_DATA_FLAG_INTERMEDIATE` sample, i.e. the nominal image after cleanup/filtering.

The program reports only WinBio HRESULTs, the chosen unit ID, size/offset metadata of the BIR header/standard/vendor/signature blocks, the returned BIR data flags, and whether a recognized ANSI-381 image header is present. It **does not save, display, hash, print, upload, or write any biometric bytes**. It calls `WinBioFree` and `WinBioCloseSession` on completion. The user should share **text output only**. The C# program has not been executed in the user's Windows guest or Windows CI; this is a diagnostic to validate there.

If it returns `E_ACCESSDENIED`, `E_NOTIMPL`, a secure-sensor error or another HRESULT, **do not disable Windows Hello, elevate outside the local authorized VM, patch the vendor driver, change registry/device policy, or install unknown fingerprint tools**. Just report the code. For a recognized standard image block, we can write a strictly local format decoder and an opt-in local-only image viewer for the next step. **Do not guess** that a vendor-specific biometric record contains directly viewable 64×80 pixels.

**Important:** Windows documents that the synchronous call may block until the application has focus and a finger is placed, and that raw-session capture requires administrative privileges. The program makes no enrollment, verification, deletion, or spoofed USB-response requests. Reference:
- https://learn.microsoft.com/en-us/windows/win32/api/winbio/nf-winbio-winbiocapturesample
- https://learn.microsoft.com/en-us/windows/win32/api/winbio/nf-winbio-winbioopensession
- https://learn.microsoft.com/en-us/windows/win32/secbiomet/winbio-bir
- https://learn.microsoft.com/en-us/windows/win32/secbiomet/winbio-bdb-ansi-381-header

## Comparison design

A screenshot of two *different* live impressions (Linux and Windows) can reveal gross differences in geometry, polarity, saturation, and ridge visibility, but cannot provide an exact pixel-level numerical comparison because finger placement/pressure changes between captures. A rigorous conversion validation would pass **the very same 5120-sample buffer** through the independently reimplemented Linux transform and the Windows DLL's image-conversion routine (inside an isolated controlled test), without using Windows Hello authentication as the test harness.

## Why not inject the Linux image into Windows Hello sign-in?

Replacing the live USB input is a **biometric-replay/authentication-bypass experiment**, not a direct converter test. It can require a modified USB transport or guest driver, disturb the working VM's authentication path, and introduce state/timing and format effects that obscure the imaging question. **We are not implementing an injection into the login path.** Prefer an offline single-buffer image converter comparison, or an explicitly isolated non-authentication vendor-engine test harness.

Keep fingerprint PNGs, BIRs, ISO/ANSI records, raw captures and templates **local**, out of Git and out of chat. Only aggregate measurements and format/status text may be shared.
