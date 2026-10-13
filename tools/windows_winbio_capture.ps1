# Windows-only, on-demand FocalTech 5955 diagnostic.
# Requires an elevated, locally interactive 64-bit PowerShell session.
# Captures ONE fresh biometric record through the Windows Biometric Service.
# Metadata only by default; biometric data written only with -SaveBIR.
# Never reads, alters, deletes or exports Windows Hello enrollments.
# SPDX-License-Identifier: LGPL-2.1-or-later
[CmdletBinding()]
param(
    [ValidateSet('Raw','Intermediate','Processed')]
    [string]$Mode='Raw',
    [switch]$SaveBIR,
    [switch]$CheckFocusOnly,
    [ValidateRange(5,120)]
    [int]$TimeoutSeconds=25,
    [string]$OutputDir=(Join-Path $env:USERPROFILE 'Desktop\FocalTech-Windows-Reference')
)
$ErrorActionPreference='Stop'
if (-not [Environment]::Is64BitProcess) {
    throw 'Run 64-bit PowerShell (not PowerShell x86).'
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Open PowerShell using Run as administrator. Raw biometric capture requires administrator permissions.'
}
if (-not ('Focal5955.WinBioCaptureV3' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace Focal5955 {
    public static class WinBioCaptureV3 {
        // WINBIO_SESSION_HANDLE and WINBIO_UNIT_ID are ULONG, not pointers.
        // WINBIO_DB_DEFAULT is the special pseudo-pointer (GUID*)1.
        [DllImport("winbio.dll", CallingConvention=CallingConvention.Winapi, ExactSpelling=true)]
        public static extern int WinBioOpenSession(
            uint factor, uint pool, uint flags,
            IntPtr units, UIntPtr count, IntPtr database, out uint session);
        [DllImport("winbio.dll", CallingConvention=CallingConvention.Winapi, ExactSpelling=true)]
        public static extern int WinBioCaptureSample(
            uint session, byte purpose, byte flags,
            out uint unit, out IntPtr sample, out UIntPtr size, out uint reject);
        [DllImport("winbio.dll", CallingConvention=CallingConvention.Winapi, ExactSpelling=true)]
        public static extern int WinBioCloseSession(uint session);
        [DllImport("winbio.dll", CallingConvention=CallingConvention.Winapi, ExactSpelling=true)]
        public static extern void WinBioFree(IntPtr sample);
        [DllImport("winbio.dll", CallingConvention=CallingConvention.Winapi, ExactSpelling=true)]
        public static extern int WinBioCancel(uint session);
        [DllImport("kernel32.dll", ExactSpelling=true)]
        private static extern IntPtr GetConsoleWindow();
        [DllImport("user32.dll", ExactSpelling=true)]
        private static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll", ExactSpelling=true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool SetForegroundWindow(IntPtr hWnd);
        public static string EnsureConsoleFocus(out bool focusOk) {
            IntPtr console = GetConsoleWindow();
            if (console == IntPtr.Zero) {
                focusOk=false;
                return "No console window found. Run in a classic, interactive PowerShell window.";
            }
            IntPtr foreground = GetForegroundWindow();
            if (foreground != console) {
                SetForegroundWindow(console);
                System.Threading.Thread.Sleep(150);
            }
            focusOk = GetForegroundWindow() == console;
            return focusOk
                ? "Console window is foreground (focus check PASS)."
                : "Console is NOT foreground (focus check FAIL). Click its title bar and rerun; do not use a detached terminal.";
        }
        private sealed class TimeoutState {
            public uint Session;
            public volatile bool Expired;
            public int CancelResult = int.MinValue;
            public System.Threading.ManualResetEvent Done = new System.Threading.ManualResetEvent(false);
        }
        // Capture stays on the foreground thread; a ThreadPool timer asks
        // Windows to cancel it if the sensor never produces a sample.
        public static int CaptureWithTimeout(uint session, byte purpose, byte flags,
            int timeoutSeconds,
            out uint unit, out IntPtr sample, out UIntPtr size, out uint reject,
            out bool timedOut, out int cancelResult) {
            var state = new TimeoutState { Session = session };
            var timer = new System.Threading.Timer(o => {
                var st = (TimeoutState)o;
                st.Expired = true;
                try { st.CancelResult = WinBioCancel(st.Session); }
                finally { st.Done.Set(); }
            }, state, checked(timeoutSeconds * 1000), System.Threading.Timeout.Infinite);
            try {
                int result = WinBioCaptureSample(session, purpose, flags,
                    out unit, out sample, out size, out reject);
                timedOut = state.Expired;
                if (timedOut) state.Done.WaitOne(4000);
                cancelResult = state.CancelResult;
                return result;
            } finally {
                timer.Change(System.Threading.Timeout.Infinite, System.Threading.Timeout.Infinite);
                timer.Dispose();
            }
        }
    }
}
'@
}
$session=[uint32]0
$unit=[uint32]0
$reject=[uint32]0
$sample=[IntPtr]::Zero
$sampleSize=[UIntPtr]::Zero
$modeFlag=@{Raw=0x20; Intermediate=0x40; Processed=0x80}[$Mode]
# WINBIO_NO_PURPOSE_AVAILABLE for raw/intermediate; VERIFY for processed.
$purpose=if ($Mode -eq 'Processed') {[byte]1} else {[byte]0}
$focused=$false
$focusMessage=[Focal5955.WinBioCaptureV3]::EnsureConsoleFocus([ref]$focused)
Write-Host $focusMessage
if($CheckFocusOnly) {
    Write-Host 'Focus-only mode. No sensor capture was requested.'
    return
}
if(-not $focused) {
    Write-Warning 'Skipping capture: the console has no foreground focus.'
    return
}
Write-Host 'Opening Windows Biometric Service (system pool, raw access)...'
$hr=[Focal5955.WinBioCaptureV3]::WinBioOpenSession(
    [uint32]8, # WINBIO_TYPE_FINGERPRINT
    [uint32]1, # WINBIO_POOL_SYSTEM
    [uint32]1, # WINBIO_FLAG_RAW=0x01; WINBIO_FLAG_DEFAULT=0x00
    [IntPtr]::Zero, [UIntPtr]::Zero, [IntPtr]::new(1),
    [ref]$session
)
Write-Host ('WinBioOpenSession HRESULT: 0x{0:X8}' -f [BitConverter]::ToUInt32([BitConverter]::GetBytes([int32]$hr),0))
if ($hr -ne 0) {
    if ([BitConverter]::ToUInt32([BitConverter]::GetBytes([int32]$hr),0) -eq 0x80070005) { Write-Host 'ACCESS DENIED: administrator privileges or sensor permissions.' }
    return
}
try {
    Write-Host ("Keep this PowerShell window focused. Lift your finger, then press the sensor again.")
    Write-Host ("Requesting {0} sample; automatic cancellation after {1} seconds..." -f $Mode,$TimeoutSeconds)
    $timedOut=$false
    $cancelHr=[int32]0
    $hr=[Focal5955.WinBioCaptureV3]::CaptureWithTimeout(
        $session,$purpose,[byte]$modeFlag,$TimeoutSeconds,
        [ref]$unit,[ref]$sample,[ref]$sampleSize,[ref]$reject,
        [ref]$timedOut,[ref]$cancelHr
    )
    Write-Host ('WinBioCaptureSample HRESULT: 0x{0:X8}' -f [BitConverter]::ToUInt32([BitConverter]::GetBytes([int32]$hr),0))
    if($timedOut){
        Write-Host ('CAPTURE TIMED OUT after {0} seconds; WinBioCancel HRESULT: 0x{1:X8}' -f $TimeoutSeconds,[BitConverter]::ToUInt32([BitConverter]::GetBytes([int32]$cancelHr),0))
    }
    Write-Host ("Sensor unit: {0}  Reject reason: {1}" -f $unit,$reject)
    if ($hr -ne 0) {
        switch ([BitConverter]::ToUInt32([BitConverter]::GetBytes([int32]$hr),0)) {
            0x80070005 { Write-Host 'ACCESS DENIED: raw sample access was refused.' }
            0x80004001 { Write-Host 'E_NOTIMPL: this sensor does not support the capture mode.' }
            0x80098008 { Write-Host 'BAD_CAPTURE: try a separate fresh press.' }
            default { Write-Host 'Capture was not successful; no biometric data saved.' }
        }
        return
    }
    $length=[UInt64]$sampleSize.ToUInt64()
    if ($sample -eq [IntPtr]::Zero -or $length -lt 32 -or $length -gt 1048576) {
        throw "Unexpected biometric record size: $length (expected 32..1048576 bytes). Not reading sample."
    }
    Write-Host ("BIR size: {0} bytes" -f $length)
    $labels=@('Header','Standard','Vendor','Signature')
    $valid=$true
    for($i=0;$i -lt 4;$i++){
        $size=[uint32][Runtime.InteropServices.Marshal]::ReadInt32($sample,$i*8)
        $offset=[uint32][Runtime.InteropServices.Marshal]::ReadInt32($sample,$i*8+4)
        Write-Host ("  {0,-9} offset={1,6} size={2,6}" -f $labels[$i],$offset,$size)
        if($size -ne 0 -and ($offset -lt 32 -or ([UInt64]$offset+[UInt64]$size) -gt $length)) {
            $valid=$false
        }
    }
    if(-not $valid) {throw 'BIR contains invalid block offsets. Refusing to save.'}
    if($SaveBIR) {
        if(-not (Test-Path -LiteralPath $OutputDir -PathType Container)) {
            New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
        }
        $out=Join-Path $OutputDir ("Focal5955-{0}-{1}.bir" -f $Mode, (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
        if(Test-Path -LiteralPath $out){throw 'Output already exists. Refusing to overwrite.'}
        $data=[byte[]]::new([int]$length)
        [Runtime.InteropServices.Marshal]::Copy($sample,$data,0,[int]$length)
        $fs=[System.IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {$fs.Write($data,0,$data.Length)} finally {$fs.Dispose()}
        [Array]::Clear($data,0,$data.Length)
        Write-Host ("Private biometric BIR written to: {0}" -f $out)
        Write-Host 'Keep this file private. Do not commit it to GitHub or paste its contents.'
    } else {
        Write-Host 'Metadata only. No biometric record saved (use -SaveBIR to opt in).'
    }
} finally {
    if($sample -ne [IntPtr]::Zero) {
        [Focal5955.WinBioCaptureV3]::WinBioFree($sample)
    }
    $closed=[Focal5955.WinBioCaptureV3]::WinBioCloseSession($session)
    Write-Host ('WinBioCloseSession HRESULT: 0x{0:X8}' -f [BitConverter]::ToUInt32([BitConverter]::GetBytes([int32]$closed),0))
}
