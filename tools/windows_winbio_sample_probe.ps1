# WinBio sample FORMAT probe for an authorized local administrator.
# Deliberately NEVER writes, previews, prints, hashes, or uploads biometric bytes.
# Tests whether Windows Biometric Framework exposes a raw/intermediate/processed
# sample from the working FocalTech 2808:5955 Windows guest.
# Usage: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows_winbio_sample_probe.ps1
#       powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows_winbio_sample_probe.ps1 -Stage Raw
# Windows PowerShell 5.1 (not PowerShell remoting); run from *local* elevated VM console.

param(
    [ValidateSet('Intermediate', 'Raw', 'Processed')]
    [string]$Stage = 'Intermediate'
)

$ErrorActionPreference = 'Stop'
if ([IntPtr]::Size -ne 8) {
    Write-Host 'Please use 64-bit Windows PowerShell, not a 32-bit PowerShell process.'
    exit 2
}
$principal = [Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'WinBio raw-session access requires an elevated local Administrator console.'
    Write-Host 'No fingerprint capture attempted.'
    exit 2
}

$source = @'
using System;
using System.Runtime.InteropServices;

public static class Ft5955WinBioFormatProbe
{
    const uint WINBIO_TYPE_FINGERPRINT = 0x08;
    const uint WINBIO_POOL_SYSTEM = 1;
    const uint WINBIO_FLAG_RAW = 1;
    const byte WINBIO_PURPOSE_VERIFY = 1;
    const byte WINBIO_NO_PURPOSE_AVAILABLE = 0;
    const byte WINBIO_DATA_FLAG_RAW = 0x20;
    const byte WINBIO_DATA_FLAG_INTERMEDIATE = 0x40;
    const byte WINBIO_DATA_FLAG_PROCESSED = 0x80;

    [DllImport("winbio.dll", ExactSpelling=true)]
    static extern int WinBioOpenSession(uint factor, uint pool, uint flags,
        IntPtr units, UIntPtr unitCount, IntPtr databaseId, out IntPtr session);

    [DllImport("winbio.dll", ExactSpelling=true)]
    static extern int WinBioCaptureSample(IntPtr session, byte purpose, byte flags,
        out uint unitId, out IntPtr sample, out UIntPtr sampleSize, out uint rejectDetail);

    [DllImport("winbio.dll", ExactSpelling=true)]
    static extern int WinBioCloseSession(IntPtr session);

    [DllImport("winbio.dll", ExactSpelling=true)]
    static extern void WinBioFree(IntPtr sample);

    static string Hr(int hr) { return "0x" + unchecked((uint)hr).ToString("X8"); }

    static void Explain(int hr) {
        uint value = unchecked((uint)hr);
        if (value == 0x80070005u)
            Console.WriteLine("Access denied: elevated raw-session access is unavailable.");
        else if (value == 0x80004001u)
            Console.WriteLine("Not implemented: driver/WinBio does not offer this capture mode.");
        else if (value == 0x8009800Fu)
            Console.WriteLine("Device state did not allow capture (WINBIO_E_INVALID_DEVICE_STATE).");
        else
            Console.WriteLine("This result needs interpretation; do not change Windows Hello settings.");
    }

    static bool InBounds(ulong total, uint offset, uint size) {
        return size > 0 && offset >= 32 && (ulong)offset + (ulong)size <= total;
    }

    static bool ReportBlock(IntPtr bir, ulong total, int fieldOffset, string label,
                            out uint offset, out uint size) {
        size = unchecked((uint)Marshal.ReadInt32(bir, fieldOffset));
        offset = unchecked((uint)Marshal.ReadInt32(bir, fieldOffset + 4));
        bool valid = (size == 0 && offset == 0) || InBounds(total, offset, size);
        Console.WriteLine("  {0}: size={1} offset={2} {3}",
                          label, size, offset, valid ? "" : "INVALID RANGE");
        return valid;
    }

    public static int Run(string stage) {
        byte dataFlag = stage == "Raw" ? WINBIO_DATA_FLAG_RAW :
                        stage == "Processed" ? WINBIO_DATA_FLAG_PROCESSED :
                        WINBIO_DATA_FLAG_INTERMEDIATE;
        byte purpose = stage == "Raw" ? WINBIO_NO_PURPOSE_AVAILABLE : WINBIO_PURPOSE_VERIFY;
        IntPtr session = IntPtr.Zero, sample = IntPtr.Zero;
        Console.WriteLine("Windows Biometric Framework format probe; one capture; NO biometric files.");
        Console.WriteLine("Requested sample stage: " + stage);
        Console.WriteLine("Guest-side WinBio API only; no direct USB commands and no Windows Hello changes.");
        try {
            // WINBIO_DB_DEFAULT is the WinBio-defined sentinel (GUID*)1 for the system pool.
            int hr = WinBioOpenSession(WINBIO_TYPE_FINGERPRINT, WINBIO_POOL_SYSTEM,
                WINBIO_FLAG_RAW, IntPtr.Zero, UIntPtr.Zero, new IntPtr(1), out session);
            Console.WriteLine("WinBioOpenSession HRESULT: " + Hr(hr));
            if (hr != 0) { Explain(hr); return 1; }

            Console.WriteLine("Now lift your finger fully, then press once. The call waits for a capture.");
            uint unit = 0, reject = 0;
            UIntPtr sampleSize = UIntPtr.Zero;
            hr = WinBioCaptureSample(session, purpose, dataFlag,
                                     out unit, out sample, out sampleSize, out reject);
            Console.WriteLine("WinBioCaptureSample HRESULT: " + Hr(hr));
            if (hr != 0) {
                Console.WriteLine("Reject-detail code: " + reject);
                Explain(hr);
                return 1;
            }
            ulong total = sampleSize.ToUInt64();
            Console.WriteLine("Biometric unit ID: " + unit);
            Console.WriteLine("BIR total bytes: " + total);
            if (sample == IntPtr.Zero || total < 32 || total > 16777216) {
                Console.WriteLine("Unexpected BIR pointer or size; refusing to inspect it.");
                return 2;
            }
            uint off, size, stdOff, stdSize;
            bool ok = ReportBlock(sample, total, 0, "Header", out off, out size);
            if (ok && InBounds(total, off, size) && size >= 5) {
                byte returned = Marshal.ReadByte(sample, checked((int)off + 4));
                Console.WriteLine("  BIR reported data-flags byte: 0x" + returned.ToString("X2"));
            }
            ok = ReportBlock(sample, total, 8, "Standard data", out stdOff, out stdSize) && ok;
            ok = ReportBlock(sample, total, 16, "Vendor data", out off, out size) && ok;
            ok = ReportBlock(sample, total, 24, "Signature", out off, out size) && ok;
            if (!ok) {
                Console.WriteLine("Malformed BIR layout; no data inspected.");
                return 2;
            }
            if (InBounds(total, stdOff, stdSize) && stdSize >= 12) {
                // Standard ANSI INCITS 381 image record: format identifier at +8.
                int id = Marshal.ReadInt32(sample, checked((int)stdOff + 8));
                Console.WriteLine("Recognized standard ANSI-381 fingerprint-image header: " +
                    (id == 0x46495200 ? "YES" : "NO / vendor-specific"));
            } else {
                Console.WriteLine("Standard image record: absent or too short to identify.");
            }
            Console.WriteLine("Fingerprint contents were not printed, saved, hashed or exported.");
            return 0;
        }
        catch (Exception ex) {
            Console.WriteLine("Probe error type: " + ex.GetType().Name);
            Console.WriteLine("No biometric data exported.");
            return 2;
        }
        finally {
            if (sample != IntPtr.Zero) WinBioFree(sample);
            if (session != IntPtr.Zero) WinBioCloseSession(session);
        }
    }
}
'@

Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop
exit [Ft5955WinBioFormatProbe]::Run($Stage)
