# Windows-only, authorized local diagnostic; capture is asynchronous and bounded.
# Does not save or disclose any biometric sample, only WinBio status and BIR sizes.
# Keep the Windows VM offline. Transfer via the already configured shared folder.
# Run elevated in the guest's focused interactive PowerShell window.
param(
    [ValidateSet('Intermediate', 'Raw', 'Processed')]
    [string]$Stage = 'Intermediate',
    [ValidateRange(5, 60)]
    [int]$TimeoutSeconds = 15
)
$ErrorActionPreference = 'Stop'
if ([IntPtr]::Size -ne 8) {
    Write-Host 'Use 64-bit Windows PowerShell.'
    exit 2
}
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Run in Windows PowerShell as Administrator; no capture attempted.'
    exit 2
}
$code = @'
using System;
using System.Runtime.InteropServices;
using System.Threading;

public static class FT5955AsyncFormatProbe {
    // WINBIO_ASYNC_RESULT is x64: Operation+8, ApiStatus+32,
    // UnitId+36, union Parameters+48; see Microsoft's Winbio.h.
    const uint FINGERPRINT = 8, SYSTEM_POOL = 1, RAW_SESSION = 1;
    const uint CALLBACK_NOTIFICATION = 1, OP_CAPTURE_SAMPLE = 12, OP_CLOSE = 2;
    static readonly ManualResetEventSlim CaptureFinished = new ManualResetEventSlim(false);
    static readonly ManualResetEventSlim CloseFinished = new ManualResetEventSlim(false);
    static CallbackDelegate CallbackReference = Completion;
    static int captureStatus = unchecked((int)0x80004005);

    [UnmanagedFunctionPointer(CallingConvention.Winapi)]
    delegate void CallbackDelegate(IntPtr asyncResult);

    [DllImport("winbio.dll", ExactSpelling = true)]
    static extern int WinBioAsyncOpenSession(uint factor, uint pool, uint flags,
        IntPtr units, UIntPtr unitCount, IntPtr databaseId,
        uint notificationMethod, IntPtr targetWindow, uint messageCode,
        CallbackDelegate callbackRoutine, IntPtr userData,
        [MarshalAs(UnmanagedType.Bool)] bool asynchronousOpen,
        out IntPtr session);

    [DllImport("winbio.dll", ExactSpelling = true)]
    static extern int WinBioCaptureSample(IntPtr session, byte purpose, byte flags,
        out uint unitId, out IntPtr sample, out UIntPtr size, out uint reject);

    [DllImport("winbio.dll", ExactSpelling = true)]
    static extern int WinBioCancel(IntPtr session);

    [DllImport("winbio.dll", ExactSpelling = true)]
    static extern int WinBioCloseSession(IntPtr session);

    [DllImport("winbio.dll", ExactSpelling = true)]
    static extern void WinBioFree(IntPtr pointer);

    static string Hr(int value) { return "0x" + unchecked((uint)value).ToString("X8"); }

    static void ReportBlock(IntPtr bir, ulong total, int offset, string label) {
        if (total < 32) return;
        uint size = unchecked((uint)Marshal.ReadInt32(bir, offset));
        uint start = unchecked((uint)Marshal.ReadInt32(bir, offset + 4));
        bool valid = (size == 0 && start == 0) ||
                     (start >= 32 && (ulong)start + (ulong)size <= total);
        Console.WriteLine("  {0}: {1} bytes ({2})", label, size,
                          valid ? "within BIR" : "INVALID RANGE");
    }

    static void Completion(IntPtr asyncResult) {
        try {
            if (asyncResult == IntPtr.Zero) return;
            int operation = Marshal.ReadInt32(asyncResult, 8);
            int status = Marshal.ReadInt32(asyncResult, 32);
            if (operation == OP_CAPTURE_SAMPLE) {
                captureStatus = status;
                Console.WriteLine("Capture completion HRESULT: " + Hr(status));
                if (status == 0) {
                    uint unit = unchecked((uint)Marshal.ReadInt32(asyncResult, 36));
                    IntPtr bir = Marshal.ReadIntPtr(asyncResult, 48);
                    ulong total = unchecked((ulong)Marshal.ReadInt64(asyncResult, 56));
                    Console.WriteLine("Unit ID: " + unit);
                    Console.WriteLine("BIR bytes: " + total);
                    if (bir != IntPtr.Zero && total >= 32 && total <= 16777216) {
                        ReportBlock(bir, total, 0, "BIR header");
                        ReportBlock(bir, total, 8, "Standard data");
                        ReportBlock(bir, total, 16, "Vendor data");
                        ReportBlock(bir, total, 24, "Signature");
                    }
                    Console.WriteLine("No biometric sample bytes printed, stored or exported.");
                } else {
                    uint reject = unchecked((uint)Marshal.ReadInt32(asyncResult, 64));
                    Console.WriteLine("Capture reject detail: " + reject);
                }
                CaptureFinished.Set();
            } else if (operation == OP_CLOSE) {
                CloseFinished.Set();
            } else {
                Console.WriteLine("WinBio asynchronous operation completed: " + operation +
                                  ", HRESULT: " + Hr(status));
            }
        } catch (Exception ex) {
            Console.WriteLine("Completion callback error type: " + ex.GetType().Name);
            CaptureFinished.Set();
        } finally {
            if (asyncResult != IntPtr.Zero) WinBioFree(asyncResult);
        }
    }

    public static int Run(string stage, int timeoutSeconds) {
        Console.WriteLine("FocalTech Windows WinBio bounded format probe (no saved biometrics).");
        Console.WriteLine("Stage: " + stage + "; timeout: " + timeoutSeconds + "s.");
        byte flag = stage == "Raw" ? (byte)0x20 :
                    stage == "Processed" ? (byte)0x80 : (byte)0x40;
        byte purpose = stage == "Raw" ? (byte)0 : (byte)1;
        IntPtr session = IntPtr.Zero;
        int hr = WinBioAsyncOpenSession(FINGERPRINT, SYSTEM_POOL, RAW_SESSION,
            IntPtr.Zero, UIntPtr.Zero, new IntPtr(1), CALLBACK_NOTIFICATION,
            IntPtr.Zero, 0, CallbackReference, IntPtr.Zero, false, out session);
        Console.WriteLine("WinBioAsyncOpenSession HRESULT: " + Hr(hr));
        if (hr != 0 || session == IntPtr.Zero)
            return 1;
        try {
            uint unit = 0, reject = 0;
            IntPtr sample = IntPtr.Zero;
            UIntPtr size = UIntPtr.Zero;
            hr = WinBioCaptureSample(session, purpose, flag, out unit,
                                     out sample, out size, out reject);
            Console.WriteLine("WinBioCaptureSample request HRESULT: " + Hr(hr));
            if (hr != 0) return 1;
            Console.WriteLine("Keep THIS PowerShell VM window in focus; lift then touch once.");
            if (!CaptureFinished.Wait(TimeSpan.FromSeconds(timeoutSeconds))) {
                Console.WriteLine("NO CAPTURE COMPLETION within timeout: " + timeoutSeconds + "s.");
                Console.WriteLine("Cancelling pending WinBio operation; not changing Windows Hello.");
                int cancel = WinBioCancel(session);
                Console.WriteLine("WinBioCancel HRESULT: " + Hr(cancel));
                if (!CaptureFinished.Wait(TimeSpan.FromSeconds(4)))
                    Console.WriteLine("Cancellation callback not received; ending probe.");
                return 3;
            }
            return captureStatus == 0 ? 0 : 1;
        } finally {
            int close = WinBioCloseSession(session);
            Console.WriteLine("WinBioCloseSession request HRESULT: " + Hr(close));
            // For an asynchronous session this completion is itself asynchronous.
            // No unbounded WinBioWait() call.
            CloseFinished.Wait(TimeSpan.FromSeconds(3));
            GC.KeepAlive(CallbackReference);
        }
    }
}
'@
Add-Type -TypeDefinition $code -Language CSharp -ErrorAction Stop
exit [FT5955AsyncFormatProbe]::Run($Stage, $TimeoutSeconds)
