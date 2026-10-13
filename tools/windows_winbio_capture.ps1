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
if (-not ('Focal5955.WinBioCapture' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace Focal5955 {
    public static class WinBioCapture {
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
Write-Host 'Opening Windows Biometric Service (system pool, raw access)...'
$hr=[Focal5955.WinBioCapture]::WinBioOpenSession(
    [uint32]8, # WINBIO_TYPE_FINGERPRINT
    [uint32]1, # WINBIO_POOL_SYSTEM
    [uint32]1, # WINBIO_FLAG_DEFAULT | WINBIO_FLAG_RAW
    [IntPtr]::Zero, [UIntPtr]::Zero, [IntPtr]::new(1),
    [ref]$session
)
Write-Host ('WinBioOpenSession HRESULT: 0x{0:X8}' -f [uint32]$hr)
if ($hr -ne 0) {
    if ([uint32]$hr -eq 0x80070005) { Write-Host 'ACCESS DENIED: administrator privileges or sensor permissions.' }
    return
}
try {
    Write-Host ("Touch the reader once when ready. Requesting {0} sample..." -f $Mode)
    $hr=[Focal5955.WinBioCapture]::WinBioCaptureSample(
        $session,$purpose,[byte]$modeFlag,
        [ref]$unit,[ref]$sample,[ref]$sampleSize,[ref]$reject
    )
    Write-Host ('WinBioCaptureSample HRESULT: 0x{0:X8}' -f [uint32]$hr)
    Write-Host ("Sensor unit: {0}  Reject reason: {1}" -f $unit,$reject)
    if ($hr -ne 0) {
        switch ([uint32]$hr) {
            0x80070005 { Write-Host 'ACCESS DENIED: raw sample access was refused.' }
            0x80004001 { Write-Host 'E_NOTIMPL: this sensor does not support the capture mode.' }
            0x80098008 { Write-Host 'BAD_CAPTURE: try a separate fresh press.' }
            default { Write-Host 'Capture was not successful; no biometric data saved.' }
        }
        return
    }
    $length=[ulong]$sampleSize.ToUInt64()
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
        if($size -ne 0 -and ($offset -lt 32 -or ([ulong]$offset+[ulong]$size) -gt $length)) {
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
        $data=New-Object byte[] ([int]$length)
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
        [Focal5955.WinBioCapture]::WinBioFree($sample)
    }
    $closed=[Focal5955.WinBioCapture]::WinBioCloseSession($session)
    Write-Host ('WinBioCloseSession HRESULT: 0x{0:X8}' -f [uint32]$closed)
}
