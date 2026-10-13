/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Adapted from OMGrant/ft9201-libfprint src/ft_engine.c (LGPL-2.1-or-later).
 * 5955 changes: fail-closed import resolution, isolated query-interface probe,
 * 9201-specific Attach/enroll disabled pending ABI validation.
 * See engine/COPYING.LGPL-2.1 and docs/5955-moh-engine-bridge.md.
 */
// loader.c — native in-process loader for ftWbioEngineAdapter.dll, NO WINE.
// Maps the PE, sets up a fake x64 TEB in %gs, runs static-CRT DllMain, then
// calls WbioQueryEngineInterface + Attach + AcceptSampleData on a real print.
//
// Build: gcc -O0 -g -o loader loader.c
// x86-64 Linux: glibc TLS uses %fs, so %gs is free for the Windows TEB.

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <errno.h>
#include "ft5955_pe_guard.h"
#include "ft5955_pe_exports.h"
#include <unistd.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <asm/prctl.h>
#include "ft5955_compat_time.h"
#include "ft5955_compat_fls.h"
#include "ft5955_compat_locale.h"
#include "ft5955_compat_datetime.h"
#include "ft5955_compat_compare.h"
#include "ft5955_compat_temp.h"
#include "ft5955_compat_cs.h"
#include "ft5955_compat_error.h"
#include "ft5955_compat_tls.h"
#include "ft5955_compat_identity.h"
#include "ft5955_compat_heap.h"
#include "ft5955_compat_sysinfo.h"
#include "ft5955_compat_env.h"
#include "ft5955_compat_slist.h"
#include "ft5955_compat_registry.h"
#include "ft5955_compat_callbacks.h"
#include "ft5955_winbio_pipeline.h"
#ifdef FT5955_OFFLINE_SENSOR_SIZE_SIM
#include "ft5955_offline_sensor_size.h"
#endif
#include "ft5955_winbio_interface_probe.h"
#include "ft5955_compat_teb_layout.h"

typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64;
#define MS __attribute__((ms_abi))
#define DLL_PROCESS_ATTACH 1

static u8 *g_image;          // mapped image base
static u64 g_imagebase;      // preferred base 0x180000000
static const char *g_dllpath;
static struct ft5955_pe_layout g_layout;

// ---------- tiny PE structures (only fields we use) ----------
#pragma pack(push,1)
typedef struct { u16 e_magic; u8 pad[58]; u32 e_lfanew; } DOS;
typedef struct {
  u32 Signature; u16 Machine, NumSecs; u32 TimeStamp, PtrSym, NumSym; u16 OptSize, Chars;
} FILEHDR;
typedef struct { u8 Name[8]; u32 VSize, VAddr, RawSize, RawPtr; u32 pad[3]; u16 pad2[2]; u32 Chars; } SEC;
#pragma pack(pop)

static u8 *g_file; static long g_filelen;
static u32 f32(u64 o){ return *(u32*)(g_file+o); }

// ---------- thread-private TEB / gs ----------
/* Never share GS/TEB state across worker threads. Preparation is idempotent:
 * repeated calls to the engine on the same pthread preserve its CRT TLS. */
static int set_gs(void *base){ return syscall(SYS_arch_prctl, ARCH_SET_GS, base); }
static int set_engine_gs_current(void){
  if(ft5955_teb_prepare_current()!=0){
    fprintf(stderr,"[5955] BLOCKED: unable to prepare current thread TEB\n");
    return -1;
  }
  const u8 *teb=ft5955_teb_view_current();
  if(!teb || set_gs((void*)teb)!=0){
    perror("[5955] BLOCKED: cannot install GS for current thread");
    return -1;
  }
  return 0;
}

// ---------- import shim table ----------
typedef struct { const char *name; void *fn; } Shim;
static Shim shims[256]; static int nshims;
static void reg(const char*n, void*f){ if(nshims>=(int)(sizeof shims/sizeof*shims)){fprintf(stderr,"ft_engine: shim table full (%d) — raise shims[]\n",nshims);abort();} shims[nshims].name=n; shims[nshims].fn=f; nshims++; }
static void* find_shim(const char*n){ for(int i=0;i<nshims;i++) if(!strcmp(shims[i].name,n)) return shims[i].fn; return 0; }

// ================= SHIMS (all MS ABI) =================


// process/thread/module
static void* MS sh_GetCurrentProcess(void){ return (void*)-1; }
static void* MS sh_GetModuleHandleW(void*n){ return (void*)g_image; }
static void* MS sh_GetModuleHandleA(void*n){ return (void*)g_image; }
static int  MS sh_GetModuleHandleExW(u32 f,void*n,void**h){ if(h)*h=(void*)g_image; return 1; }
static u32  MS sh_GetModuleFileNameA(void*m,char*b,u32 n){ strncpy(b,g_dllpath,n); return strlen(g_dllpath); }
static u32  MS sh_GetModuleFileNameW(void*m,u16*b,u32 n){ u32 i=0; for(;g_dllpath[i]&&i<n-1;i++) b[i]=g_dllpath[i]; b[i]=0; return i; }
static void* MS sh_LoadLibraryExW(void*n,void*h,u32 f){ return (void*)0x1000; }
static int  MS sh_FreeLibrary(void*h){ return 1; }
static void* MS sh_GetProcAddress(void*h,const char*n){ if((u64)n>>16==0) return 0; /*by ordinal*/ return find_shim(n); }

// console/file → route engine logs to stderr so we SEE its [Engine] output
static void* MS sh_GetStdHandle(u32 n){ return (void*)(u64)(n?n:1); }
static int  MS sh_SetStdHandle(u32 n,void*h){ return 1; }
static u32  MS sh_GetFileType(void*h){ return 2; /*CHAR*/ }
static int  MS sh_GetConsoleMode(void*h,u32*m){ if(m)*m=0; return 1; }
static u32  MS sh_GetConsoleCP(void){ return 437; }
static int  MS sh_WriteFile(void*h,const void*b,u32 n,u32*wr,void*o){ fwrite(b,1,n,stderr); if(wr)*wr=n; return 1; }
static int  MS sh_WriteConsoleW(void*h,const u16*b,u32 n,u32*wr,void*r){ for(u32 i=0;i<n;i++) fputc(b[i]&0xff,stderr); if(wr)*wr=n; return 1; }
static void MS sh_OutputDebugStringA(const char*s){ fprintf(stderr,"%s",s?s:""); }
static void MS sh_OutputDebugStringW(const u16*s){ if(s)for(;*s;s++) fputc(*s&0xff,stderr); }
static int  MS sh_FlushFileBuffers(void*h){ return 1; }
static void* MS sh_CreateFileW(void*n,u32 a,u32 s,void*sa,u32 c,u32 fl,void*t){ ft5955_SetLastError(2); return (void*)-1; } // config absent → graceful
static int  MS sh_SetFilePointerEx(void*h,long long d,void*np,u32 m){ return 0; }
static int  MS sh_CloseHandle(void*h){ return 1; }
static void* MS sh_FindFirstFileExA(void*n,int i,void*d,int o,void*s,u32 f){ return (void*)-1; }
static int  MS sh_FindNextFileA(void*h,void*d){ return 0; }
static int  MS sh_FindClose(void*h){ return 1; }
static u32  MS sh_GetSystemDirectoryA(char*b,u32 n){ strncpy(b,"C:\\Windows\\System32",n); return 19; }

// sync / events → the engine's global lock
static void* MS sh_CreateEventW(void*sa,int man,int init,void*name){ return (void*)0x2000; }
static int  MS sh_SetEvent(void*h){ return 1; }
static int  MS sh_ResetEvent(void*h){ return 1; }
static u32  MS sh_WaitForSingleObject(void*h,u32 ms){ return 0; /*WAIT_OBJECT_0*/ }
static u32  MS sh_WaitForSingleObjectEx(void*h,u32 ms,int a){ return 0; }
static void* MS sh_CreateThread(void*sa,u64 st,void*fn,void*arg,u32 fl,u32*id){ if(id)*id=4321; return (void*)0x3000; }
static int MS sh_DeviceIoControl(void*h,u32 c,void*ib,u32 il,void*ob,u32 ol,u32*ret,void*ov){
  (void)h;(void)ib;(void)il;(void)ov;
#ifdef FT5955_OFFLINE_SENSOR_SIZE_SIM
  if(c==FT5955_IOCTL_BIOMETRIC_SENSOR_SIZE) {
    int success=ft5955_sim_sensor_ioctl(c,ob,ol,ret);
    fprintf(stderr,"[5955] SYNTHETIC sensor-size IOCTL: %ux%u; status=%d\n",
            (unsigned)FT5955_SIM_WIDTH,(unsigned)FT5955_SIM_HEIGHT,success);
    return success;
  }
#endif
  if(ret)*ret=0;
  ft5955_SetLastError(1); /* ERROR_INVALID_FUNCTION; unsupported IOCTL */
  return 0;
}

// locale / codepage (ucrt init)
static u32  MS sh_GetACP(void){ return 1252; }
static u32  MS sh_GetOEMCP(void){ return 437; }
static int  MS sh_GetCPInfo(u32 cp,void*info){ if(info){ u8*p=info; *(u32*)p=1; p[4]=0; p[5]=0; } return 1; }
static int  MS sh_IsValidCodePage(u32 cp){ return 1; }
static int  MS sh_MultiByteToWideChar(u32 cp,u32 f,const char*mb,int mbc,u16*wc,int wcc){
  if(mbc<0) mbc=strlen(mb)+1;
  if(wcc==0) return mbc;
  int n=mbc<wcc?mbc:wcc;
  for(int i=0;i<n;i++) wc[i]=(u8)mb[i];
  return n; }
static int  MS sh_WideCharToMultiByte(u32 cp,u32 f,const u16*wc,int wcc,char*mb,int mbc,void*d,void*u){
  if(wcc<0){ wcc=0; while(wc[wcc]) wcc++; wcc++; } if(mbc==0) return wcc; int n=wcc<mbc?wcc:mbc; for(int i=0;i<n;i++) mb[i]=(char)wc[i]; return n; }
static int  MS sh_LCMapStringW(u32 l,u32 f,const u16*s,int sc,u16*d,int dc){ if(dc==0) return sc; int n=sc<dc?sc:dc; for(int i=0;i<n;i++) d[i]=s[i]; return n; }
static int  MS sh_GetStringTypeW(u32 t,const u16*s,int c,u16*out){ for(int i=0;i<c;i++) out[i]=0; return 1; }

// misc / version / cpu
static int  MS sh_IsDebuggerPresent(void){ return 0; }
static int  MS sh_IsProcessorFeaturePresent(u32 f){ return 1; }
static void* MS sh_EncodePointer(void*p){ return p; }
static void* MS sh_DecodePointer(void*p){ return p; }
static u64  MS sh_VerSetConditionMask(u64 m,u32 t,u8 c){ return m; }
static int  MS sh_VerifyVersionInfoA(void*vi,u32 tm,u64 cm){ return 1; }
static char g_cmd[]="loader"; static u16 g_cmdw[]={'l','o','a','d','e','r',0};
static char* MS sh_GetCommandLineA(void){ return g_cmd; }
static u16*  MS sh_GetCommandLineW(void){ return g_cmdw; }
static void MS sh_GetStartupInfoW(void*si){ memset(si,0,104); *(u32*)si=104; }

// exception/unwind (only hit if the engine throws — hope not)
static void MS sh_RtlCaptureContext(void*ctx){ memset(ctx,0,1232); }
static void* MS sh_RtlLookupFunctionEntry(u64 pc,u64*base,void*hist){ if(base)*base=g_imagebase; return 0; }
static void* MS sh_RtlVirtualUnwind(u32 t,u64 b,u64 pc,void*fe,void*ctx,void**hd,u64*est,void*ctxp){ return 0; }
static void MS sh_RtlUnwindEx(void*a,void*b,void*c,void*d,void*e,void*f){ }
static void* MS sh_RtlPcToFileHeader(void*pc,void**base){ if(base)*base=(void*)g_image; return (void*)g_image; }
static void* MS sh_SetUnhandledExceptionFilter(void*f){ return 0; }
static u32  MS sh_UnhandledExceptionFilter(void*p){ return 1; }
static void MS sh_RaiseException(u32 code,u32 fl,u32 n,void*a){ fprintf(stderr,"[!] RaiseException code=%#x\n",code); }
static void MS sh_TerminateProcess(void*h,u32 c){ fprintf(stderr,"[!] TerminateProcess(%u)\n",c); }
static void MS sh_ExitProcess(u32 c){ fprintf(stderr,"[!] ExitProcess(%u)\n",c); }


/* 5955 MOH import closure: deliberately failure-only placeholders.
 * These satisfy import resolution ONLY. None emulate successful Windows I/O.
 * DLL execution MUST remain disabled until every called API is implemented
 * and ABI/side effects are audited. In particular, RtlUnwind must not return
 * as though stack unwinding succeeded. No Linux FS, USB or event log access. */
#define FT5955_UNSUPPORTED 120u /* ERROR_CALL_NOT_IMPLEMENTED */
static int MS sh_SetEndOfFile(void *h) {
  (void)h; ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_ReadFile(void *h,void *buf,u32 n,u32 *read_count,void *overlapped) {
  (void)h;(void)buf;(void)n;(void)overlapped;
  if(read_count) *read_count=0;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_ReadConsoleW(void *h,void *buf,u32 n,u32 *read_count,void *control) {
  (void)h;(void)buf;(void)n;(void)control;
  if(read_count) *read_count=0;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_GetFileSizeEx(void *h,int64_t *size) {
  (void)h;
  if(size) *size=0;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_GetFileAttributesExW(const u16 *name,u32 level,void *info) {
  (void)name;(void)level;(void)info;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_CreateDirectoryW(const u16 *name,void *sa) {
  (void)name;(void)sa;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static void * MS sh_FindFirstFileExW(const u16 *name,u32 info_level,void *data,
                                    u32 search_op,void *filter,u32 flags) {
  (void)name;(void)info_level;(void)data;(void)search_op;(void)filter;(void)flags;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return (void *)(intptr_t)-1;
}
static int MS sh_FindNextFileW(void *find,void *data) {
  (void)find;(void)data;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_SetConsoleCtrlHandler(void *handler,int add) {
  (void)handler;(void)add;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static void MS sh_RtlUnwind(void *target_frame,void *target_ip,
                            void *record,void *retval) {
  (void)target_frame;(void)target_ip;(void)record;(void)retval;
  fputs("[5955] FATAL: unsupported RtlUnwind reached; aborting safely\\n",stderr);
  abort();
}
static int MS sh_ReportEventA(void *source,u16 type,u16 category,u32 event_id,
                               void *user_sid,u16 count,u32 data_size,
                               const char *const *strings,const void *raw) {
  (void)source;(void)type;(void)category;(void)event_id;(void)user_sid;
  (void)count;(void)data_size;(void)strings;(void)raw;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static void * MS sh_RegisterEventSourceA(const char *server,const char *source) {
  (void)server;(void)source;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_DeregisterEventSource(void *source) {
  (void)source;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_SetupDiDestroyDeviceInfoList(void *set) {
  (void)set; ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_SetupDiEnumDeviceInfo(void *set,u32 index,void *info) {
  (void)set;(void)index;(void)info;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static int MS sh_SetupDiGetDeviceInstanceIdA(void *set,void *info,char *id,
                                             u32 length,u32 *required) {
  (void)set;(void)info;(void)id;(void)length;
  if(required) *required=0;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}
static void * MS sh_SetupDiGetClassDevsA(const void *guid,const char *enumerator,
                                         void *parent,u32 flags) {
  (void)guid;(void)enumerator;(void)parent;(void)flags;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return (void *)(intptr_t)-1;
}
static int MS sh_SetupDiClassGuidsFromNameExA(const char *class_name,void *guids,
                                              u32 count,u32 *required,
                                              const char *machine,void *reserved) {
  (void)class_name;(void)guids;(void)count;(void)machine;(void)reserved;
  if(required) *required=0;
  ft5955_SetLastError(FT5955_UNSUPPORTED); return 0;
}

static void __attribute__((unused)) register_shims(void){
#define R(n) reg(#n, (void*)sh_##n)
  /* Import closure only: these 18 functions are NOT runtime-compatible. */
  R(SetEndOfFile);R(ReadFile);R(ReadConsoleW);R(GetFileSizeEx);
  R(GetFileAttributesExW);R(CreateDirectoryW);
  R(FindFirstFileExW);R(FindNextFileW);R(SetConsoleCtrlHandler);
  R(RtlUnwind);R(ReportEventA);R(RegisterEventSourceA);R(DeregisterEventSource);
  R(SetupDiDestroyDeviceInfoList);R(SetupDiEnumDeviceInfo);
  R(SetupDiGetDeviceInstanceIdA);R(SetupDiGetClassDevsA);
  R(SetupDiClassGuidsFromNameExA);
  reg("SetLastError", (void*)ft5955_SetLastError);
  reg("GetLastError", (void*)ft5955_GetLastError);
  reg("GetProcessHeap", (void*)ft5955_GetProcessHeap);
  reg("HeapAlloc", (void*)ft5955_HeapAlloc);
  reg("HeapFree", (void*)ft5955_HeapFree);
  reg("HeapReAlloc", (void*)ft5955_HeapReAlloc);
  reg("HeapSize", (void*)ft5955_HeapSize);
  reg("HeapValidate", (void*)ft5955_HeapValidate);
  reg("HeapQueryInformation", (void*)ft5955_HeapQueryInformation);
  reg("InitializeCriticalSection", (void*)ft5955_InitializeCriticalSection);
  reg("InitializeCriticalSectionAndSpinCount", (void*)ft5955_InitializeCriticalSectionAndSpinCount);
  reg("EnterCriticalSection", (void*)ft5955_EnterCriticalSection);
  reg("LeaveCriticalSection", (void*)ft5955_LeaveCriticalSection);
  reg("DeleteCriticalSection", (void*)ft5955_DeleteCriticalSection);
  reg("InitializeSListHead", (void*)ft5955_InitializeSListHead);
  reg("InterlockedFlushSList", (void*)ft5955_InterlockedFlushSList);
  reg("InterlockedPushEntrySList", (void*)ft5955_InterlockedPushEntrySList);
  reg("TlsAlloc", (void*)ft5955_TlsAlloc);
  reg("TlsFree", (void*)ft5955_TlsFree);
  reg("TlsGetValue", (void*)ft5955_TlsGetValue);
  reg("TlsSetValue", (void*)ft5955_TlsSetValue);
  reg("FlsAlloc", (void*)ft5955_FlsAlloc);
  reg("FlsGetValue", (void*)ft5955_FlsGetValue);
  reg("FlsSetValue", (void*)ft5955_FlsSetValue);
  reg("FlsFree", (void*)ft5955_FlsFree);
  R(GetCurrentProcess);
  reg("GetCurrentProcessId", (void*)ft5955_GetCurrentProcessId);
  reg("GetCurrentThreadId", (void*)ft5955_GetCurrentThreadId);
  reg("GetCurrentThread", (void*)ft5955_GetCurrentThread);
  R(GetModuleHandleW);R(GetModuleHandleA);R(GetModuleHandleExW);R(GetModuleFileNameA);R(GetModuleFileNameW);
  R(LoadLibraryExW);R(FreeLibrary);R(GetProcAddress);
  R(GetStdHandle);R(SetStdHandle);R(GetFileType);R(GetConsoleMode);R(GetConsoleCP);
  reg("GetConsoleOutputCP", (void*)ft5955_GetConsoleOutputCP);
  R(WriteFile);R(WriteConsoleW);R(OutputDebugStringA);R(OutputDebugStringW);R(FlushFileBuffers);
  R(CreateFileW);R(SetFilePointerEx);R(CloseHandle);R(FindFirstFileExA);R(FindNextFileA);R(FindClose);R(GetSystemDirectoryA);
  R(CreateEventW);R(SetEvent);R(ResetEvent);R(WaitForSingleObject);R(WaitForSingleObjectEx);R(CreateThread);R(DeviceIoControl);
  R(GetACP);R(GetOEMCP);R(GetCPInfo);R(IsValidCodePage);R(MultiByteToWideChar);R(WideCharToMultiByte);R(LCMapStringW);R(GetStringTypeW);
  reg("GetUserDefaultLCID", (void*)ft5955_GetUserDefaultLCID);
  reg("IsValidLocale", (void*)ft5955_IsValidLocale);
  reg("GetLocaleInfoW", (void*)ft5955_GetLocaleInfoW);
  reg("GetTempPathW", (void*)ft5955_GetTempPathW);
  reg("CompareStringW", (void*)ft5955_CompareStringW);
  reg("EnumSystemLocalesW", (void*)ft5955_EnumSystemLocalesW);
  reg("GetDateFormatW", (void*)ft5955_GetDateFormatW);
  reg("GetTimeFormatW", (void*)ft5955_GetTimeFormatW);
  reg("GetSystemInfo", (void*)ft5955_GetSystemInfo);
  reg("GetSystemTimeAsFileTime", (void*)ft5955_GetSystemTimeAsFileTime);
  reg("GetTickCount", (void*)ft5955_GetTickCount);
  reg("QueryPerformanceCounter", (void*)ft5955_QueryPerformanceCounter);
  reg("QueryPerformanceFrequency", (void*)ft5955_QueryPerformanceFrequency);
  reg("Sleep", (void*)ft5955_Sleep);
  reg("GetLocalTime", (void*)ft5955_GetLocalTime);
  R(IsDebuggerPresent);R(IsProcessorFeaturePresent);
  R(EncodePointer);R(DecodePointer);R(VerSetConditionMask);R(VerifyVersionInfoA);
  R(GetCommandLineA);R(GetCommandLineW);R(GetStartupInfoW);
  reg("GetEnvironmentStringsW", (void*)ft5955_GetEnvironmentStringsW);
  reg("FreeEnvironmentStringsW", (void*)ft5955_FreeEnvironmentStringsW);
  reg("SetEnvironmentVariableW", (void*)ft5955_SetEnvironmentVariableW);
  reg("RegOpenKeyExA", (void*)ft5955_RegOpenKeyExA);
  reg("RegQueryValueExA", (void*)ft5955_RegQueryValueExA);
  reg("RegCloseKey", (void*)ft5955_RegCloseKey);
  reg("RegSetKeyValueA", (void*)ft5955_RegSetKeyValueA);
  R(RtlCaptureContext);R(RtlLookupFunctionEntry);R(RtlVirtualUnwind);R(RtlUnwindEx);R(RtlPcToFileHeader);
  R(SetUnhandledExceptionFilter);R(UnhandledExceptionFilter);R(RaiseException);R(TerminateProcess);R(ExitProcess);
#undef R
}

// ================= PE LOADER =================
static int __attribute__((unused)) load_pe(void){
  /* Reject directories, symlinks, huge and truncated files *before* reading
   * even the DOS e_lfanew offset or copying a PE section. */
  int fd=open(g_dllpath,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
  if(fd<0){ perror("[5955] open MOH DLL"); return -1; }
  struct stat statbuf;
  if(fstat(fd,&statbuf)!=0 || !S_ISREG(statbuf.st_mode) ||
     statbuf.st_size < 0x100 || statbuf.st_size > FT5955_PE_FILE_LIMIT){
    fprintf(stderr,"[5955] BLOCKED: unsupported PE file type/size\n");
    close(fd);
    return -1;
  }
  g_filelen=(long)statbuf.st_size;
  g_file=malloc((size_t)g_filelen);
  if(!g_file){ close(fd); return -1; }
  size_t total_read=0;
  while(total_read<(size_t)g_filelen){
    ssize_t got=read(fd,g_file+total_read,(size_t)g_filelen-total_read);
    if(got<0 && errno==EINTR) continue;
    if(got<=0){
      fprintf(stderr,"[5955] BLOCKED: could not read complete PE file\n");
      free(g_file); g_file=NULL; close(fd); return -1;
    }
    total_read+=(size_t)got;
  }
  close(fd);

  struct ft5955_pe_layout layout;
  if(ft5955_pe_guard(g_file,(size_t)g_filelen,&layout)!=0){
    fprintf(stderr,"[5955] BLOCKED: PE headers/sections invalid or unsupported\n");
    free(g_file); g_file=NULL;
    return -4;
  }
  g_imagebase=layout.image_base;
  u32 sizeofimage=layout.image_size;
  u32 entry=layout.entry_rva;
  u16 nsec=layout.section_count;
  u64 sectbl=layout.section_table;
  u32 hdrsize=layout.headers_size; // verified on-disk SizeOfHeaders
  g_layout=layout;

  /* The SHA-verified 5955 MOH DLL has no PE TLS directory. Never execute
   * the FT9201 loader's old callbacks, especially before installing GS.
   * Any different DLL with a TLS directory is unsupported and fails closed. */
  /* Guard rejected both TLS directory RVA and size before any copies. */

  /* Prepare the fully-resolved image in a scratch buffer (writable, NOT
   * executable), then map it back from an anonymous FILE (memfd) with per-section
   * protections. This keeps code read+execute and data read+write, so no page is
   * ever writable AND executable at once — which lets the engine run under
   * fprintd's MemoryDenyWriteExecute=yes hardening (no systemd override needed).
   * The DLL loads at its preferred base 0x180000000, so no relocations are
   * required. */
  u8 *img=calloc(1,sizeofimage);
  if(!img){ perror("calloc"); return -1; }
  memcpy(img,g_file,hdrsize);
  for(int i=0;i<nsec;i++){
    u64 s=sectbl+i*40;
    u32 vaddr=f32(s+12), rawsize=f32(s+16), rawptr=f32(s+20);
    memcpy(img+vaddr, g_file+rawptr, rawsize);
  }

  /* Resolve imports ONLY within the guarded scratch-image boundaries.
   * Every import descriptor, thunk and hint/name must fit the PE image.
   * Malformed unterminated tables fail before memfd/mmap/DllMain. */
  u32 imprva=layout.import_rva;
  int unresolved_imports=0;
  int descriptors_terminated=0;
  for(u64 d=imprva; d+20 <= (u64)imprva+layout.import_size; d+=20){
    u32 orig=*(u32*)(img+d), namer=*(u32*)(img+d+12), fthunk=*(u32*)(img+d+16);
    if(namer==0){ descriptors_terminated=1; break; }
    if(namer>=sizeofimage || !memchr(img+namer,0,sizeofimage-namer)){
      fprintf(stderr,"[loader] BLOCKED: invalid import-library string\n");
      unresolved_imports++; break;
    }
    u64 rt=orig?orig:fthunk;
    if(rt>=sizeofimage || fthunk>=sizeofimage){
      fprintf(stderr,"[loader] BLOCKED: import thunk outside PE image\n");
      unresolved_imports++; break;
    }
    int thunks_terminated=0;
    for(u64 j=0; j < sizeofimage/8u; j++){
      u64 readat=rt+j*8u, writeat=(u64)fthunk+j*8u;
      if(readat+8u>sizeofimage || writeat+8u>sizeofimage){
        fprintf(stderr,"[loader] BLOCKED: import thunk exceeds PE image\n");
        unresolved_imports++; break;
      }
      u64 ent=*(u64*)(img+readat);
      if(!ent){ thunks_terminated=1; break; }
      if(ent>>63){
        fprintf(stderr,"[loader] UNSUPPORTED ordinal import\n");
        unresolved_imports++; continue;
      }
      u32 name_rva=(u32)ent;
      if((u64)name_rva+2u>=sizeofimage ||
         !memchr(img+name_rva+2u,0,sizeofimage-name_rva-2u)){
        fprintf(stderr,"[loader] BLOCKED: invalid import-function name\n");
        unresolved_imports++; break;
      }
      const char*fn=(char*)(img+name_rva+2u);
      void*sh=find_shim(fn);
      if(!sh){
        fprintf(stderr,"[loader] MISSING shim: %s\n",fn);
        unresolved_imports++; continue;
      }
      *(u64*)(img+writeat)=(u64)sh;
    }
    if(!thunks_terminated){
      unresolved_imports++;
      break;
    }
  }
  if(!descriptors_terminated){
    fprintf(stderr,"[loader] BLOCKED: invalid/unterminated import descriptors\n");
    unresolved_imports++;
  }

  /* Never execute DLL TLS callbacks or DllMain with unresolved imports. */
  if(unresolved_imports){
    fprintf(stderr,"[loader] BLOCKED: %d unresolved Windows imports; DLL NOT executed\n",unresolved_imports);
    free(img);
    return -3;
  }

  /* write the prepared image to an anonymous in-memory file */
  int mfd=memfd_create("ftengine",MFD_CLOEXEC);
  if(mfd<0){ perror("memfd_create"); free(img); return -1; }
  ssize_t wr=write(mfd,img,sizeofimage);
  free(img);
  if(wr!=(ssize_t)sizeofimage){ perror("write memfd"); close(mfd); return -1; }

  /* reserve the preferred base, then map each section from the file (W^X-safe) */
  void *m=mmap((void*)g_imagebase,sizeofimage,PROT_NONE,
               MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
  if(m==MAP_FAILED || m!=(void*)g_imagebase){
    fprintf(stderr,"[loader] reserve @%#lx failed (%p)\n",g_imagebase,m); close(mfd); return -1;
  }
  g_image=m;
  u32 hdrmap=(hdrsize+0xfff)&~0xfffu;
  if(mmap(g_image,hdrmap,PROT_READ,MAP_PRIVATE|MAP_FIXED,mfd,0)==MAP_FAILED){
    perror("[loader] map headers"); close(mfd); return -1;
  }
  for(int i=0;i<nsec;i++){
    u64 s=sectbl+i*40;
    u32 vaddr=f32(s+12), vsize=f32(s+8), rawsize=f32(s+16), chars=f32(s+36);
    u32 seglen=(vsize>rawsize?vsize:rawsize); seglen=(seglen+0xfff)&~0xfffu;
    if(vaddr+seglen>sizeofimage) seglen=sizeofimage-vaddr;
    if(!seglen) continue;
    int prot=PROT_READ;
    if(chars&0x20000000) prot|=PROT_EXEC;   // IMAGE_SCN_MEM_EXECUTE
    if(chars&0x80000000) prot|=PROT_WRITE;  // IMAGE_SCN_MEM_WRITE
    if(mmap(g_image+vaddr,seglen,prot,MAP_PRIVATE|MAP_FIXED,mfd,vaddr)==MAP_FAILED){
      perror("[loader] map section"); close(mfd); return -1;
    }
  }
  close(mfd);
  fprintf(stderr,"[loader] file-backed image at %#lx (no W+X), entry RVA %#x\n",g_imagebase,entry);

  /* TLS callback execution is deliberately unsupported for this MOH path.
   * The pinned DLL has NO TLS directory. Install the per-thread TEB/GS
   * only after import resolution, before any vendor DllMain entry. */
  if(set_engine_gs_current()!=0) return -5;
  fprintf(stderr,"[loader] per-thread TEB installed in %%gs\n");

  // run entry point (DllMain via CRT startup)
  int(MS *DllMain)(void*,u32,void*)=(void*)(g_image+entry);
  fprintf(stderr,"[loader] calling entry (DllMain) ...\n");
  int r=DllMain((void*)g_imagebase,DLL_PROCESS_ATTACH,0);
  fprintf(stderr,"[loader] DllMain returned %d\n",r);
  return r?0:-2;
}

// Resolve an export by name only through a bounded PE export directory.
// Never call a forwarded export or pointer outside an executable section.
static __attribute__((unused)) void* get_export(const char*want){
  if(!g_image || !g_file || !g_layout.image_size) return 0;
  const u64 direntry=(u64)g_layout.nt_offset+24+112;
  const u32 exprva=f32(direntry);
  const u32 expsize=f32(direntry+4);
  u32 function_rva=0;
  if(ft5955_pe_find_export(g_image,g_layout.image_size,exprva,expsize,
                           want,&function_rva)!=0) return 0;
  for(u32 i=0;i<g_layout.section_count;i++){
    const u64 at=g_layout.section_table+(u64)i*40u;
    const u32 size=f32(at+8),rva=f32(at+12),raw=f32(at+16),flags=f32(at+36);
    const u32 span=size>raw?size:raw;
    if(function_rva>=rva && (u64)function_rva-rva<span &&
       (flags&0x20000000u)) return g_image+function_rva;
  }
  fprintf(stderr,"[5955] BLOCKED: PE export outside executable section\n");
  return 0;
}

// ================= engine driving (mirrors the Go harness) =================
/* WINBIO_PIPELINE is 0x50 bytes on Win64. Attach remains compile-time gated. */
static ft5955_winbio_pipeline pipeline;
static u8 birbuf[262144];

static u8 small[262144];
static void resize(u8*src,int sw,int sh,int dw,int dh){ for(int y=0;y<dh;y++)for(int x=0;x<dw;x++) small[y*dw+x]=src[(y*sh/dh)*sw+(x*sw/dw)]; }
// Prepare an ENG_W x ENG_H frame in `small`. If the source is at least as large,
// crop the CENTERED window (preserves true ridge geometry — no aspect distortion);
// otherwise scale. FT9201_SCALE forces the old scale path for A/B testing.
#define FRAME_W 64
#define FRAME_H 80
static void prepare_frame(const u8*src,int sw,int sh){
  if(sw>=FRAME_W && sh>=FRAME_H && !getenv("FT9201_SCALE")){
    int ox=(sw-FRAME_W)/2, oy=(sh-FRAME_H)/2;
    for(int y=0;y<FRAME_H;y++) for(int x=0;x<FRAME_W;x++) small[y*FRAME_W+x]=src[(oy+y)*sw+(ox+x)];
  } else {
    resize((u8*)src, sw, sh, FRAME_W, FRAME_H);
  }
}
static int build_bir(u8*pix,int w,int h){
  int total=0x48+0x38+w*h; memset(birbuf,0,total);
  const int HDR=0x18,STD=0x48;
  *(u32*)(birbuf+0)=0x30; *(u32*)(birbuf+4)=HDR;
  *(u32*)(birbuf+8)=0x38+w*h; *(u32*)(birbuf+0xc)=STD;
  *(u16*)(birbuf+HDR+0x28)=0x001B; *(u16*)(birbuf+HDR+0x2a)=0x0401;
  *(u16*)(birbuf+STD+0x1c)=500; *(u16*)(birbuf+STD+0x1e)=500;
  birbuf[STD+0x22]=8; birbuf[STD+0x23]=0;
  *(u16*)(birbuf+STD+0x2c)=w; *(u16*)(birbuf+STD+0x2e)=h;
  memcpy(birbuf+STD+0x38,pix,w*h);
  return total;
}

// ================= STORAGE ADAPTER STUB (pipeline+0x28 vtable) =================
// Vtable: 0x20 header + function slots (standard WINBIO_STORAGE_INTERFACE order).
// Offsets the engine calls (verified by disassembly):
//   +0x68 AddRecord  +0x78 QueryBySubject  +0x90 FirstRecord
//   +0x98 NextRecord +0xa0 GetCurrentRecord
// WINBIO_STORAGE_RECORD fields the engine uses: +0x00 Identity*, +0x20 TemplateBlob,
//   +0x28 TemplateBlobSize.
static u8  g_rec_identity[76];
static u8  g_rec_template[1<<20];   // enrollment template can be ~200KB (up to 18 sub-tpls)
static u64 g_rec_tsize = 0;
static int g_have_record = 0;

/* Unknown sensor/storage methods MUST NOT report S_OK. This generic
 * placeholder is a fail-closed tripwire, not a substitute for an audited
 * method-specific callback signature or a complete WinBio interface. */


static u32 MS st_QueryBySubject(void*pipe,void*identity,u8 sub){
  fprintf(stderr,"[storage] QueryBySubject(sub=%u) -> %s\n", sub,
          g_have_record?"S_OK":"NO_RESULTS");
  if(identity) memcpy(g_rec_identity, identity, sizeof g_rec_identity);
  return g_have_record ? 0 : 0x8009801f; // WINBIO_E_DATABASE_NO_RESULTS
}
static u32 MS st_FirstRecord(void*pipe){
  fprintf(stderr,"[storage] FirstRecord -> %s\n", g_have_record?"S_OK":"NO_RESULTS");
  return g_have_record ? 0 : 0x8009801f;
}
static u32 MS st_NextRecord(void*pipe){
  fprintf(stderr,"[storage] NextRecord -> NO_MORE_RECORDS\n");
  return 0x80098020; // single-record store: always end after the first
}
static u32 MS st_GetCurrentRecord(void*pipe,u8*rec){
  fprintf(stderr,"[storage] GetCurrentRecord (tsize=%lu)\n",(unsigned long)g_rec_tsize);
  memset(rec,0,0x40);
  *(u64*)(rec+0x00)=(u64)g_rec_identity;
  *(u64*)(rec+0x20)=(u64)g_rec_template;
  *(u64*)(rec+0x28)=g_rec_tsize;
  return 0;
}
static u32 MS st_AddRecord(void*pipe,u8*rec,u8 sub){
  u64 tp=*(u64*)(rec+0x20), ts=*(u64*)(rec+0x28);
  u64 idp=*(u64*)(rec+0x00);
  fprintf(stderr,"[storage] AddRecord(sub=%u) template=%#lx size=%lu\n",sub,(unsigned long)tp,(unsigned long)ts);
  if(idp) memcpy(g_rec_identity,(void*)idp,sizeof g_rec_identity);
  if(tp && ts && ts<=sizeof g_rec_template){ memcpy(g_rec_template,(void*)tp,ts); g_rec_tsize=ts; g_have_record=1; }
  return 0;
}

/* Inert adapter tables: valid common header layout, but the actual
 * adapter IDs, version negotiation and method signatures remain unverified.
 * The Attach path remains compile-time disabled. */
static ft5955_winbio_interface_probe g_storage_vt;
static ft5955_winbio_interface_probe g_sensor_vt;
#define FT5955_SLOT(offset) (((offset)-0x20u)/8u)
static void __attribute__((unused)) build_storage_vtable(void){
  ft5955_winbio_interface_probe_init(&g_storage_vt,FT5955_WINBIO_STORAGE_TYPE);
  ft5955_winbio_interface_probe_init(&g_sensor_vt,FT5955_WINBIO_SENSOR_TYPE);
  for(size_t i=0;i<FT5955_WINBIO_PROBE_SLOTS;i++){
    g_storage_vt.slots[i]=(u64)ft5955_unimplemented_callback;
    g_sensor_vt.slots[i]=(u64)ft5955_unimplemented_callback;
  }
  g_storage_vt.slots[FT5955_SLOT(0x68)]=(u64)st_AddRecord;
  g_storage_vt.slots[FT5955_SLOT(0x78)]=(u64)st_QueryBySubject;
  g_storage_vt.slots[FT5955_SLOT(0x90)]=(u64)st_FirstRecord;
  g_storage_vt.slots[FT5955_SLOT(0x98)]=(u64)st_NextRecord;
  g_storage_vt.slots[FT5955_SLOT(0xa0)]=(u64)st_GetCurrentRecord;
}
#undef FT5955_SLOT


/* ==================== public API (ft_engine.h) ==================== */
#include "ft_engine.h"
#define ENG_W 64
#define ENG_H 80
static void *g_iface;

void ft_engine_geometry(int *w,int *h){ if(w)*w=ENG_W; if(h)*h=ENG_H; }

static int g_loaded __attribute__((unused)) = 0;
/* Experimental 5955-only interface smoke-test. Does NOT Attach, enroll or
 * use USB. Run only in an offline, isolated test environment. */
int ft_engine_smoke_interface(const char *dll_path){
#ifndef FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT
  (void)dll_path;
  fprintf(stderr,"[5955] BLOCKED: runtime shim and MOH engine ABI audit not yet complete\n");
  return -100;
#else
  g_dllpath=dll_path;
  register_shims();
  if(load_pe()!=0) return -1;
  void *q=get_export("WbioQueryEngineInterface");
  if(!q) return -2;
  u64 (MS *Query)(void**)=q;
  void *iface=0;
  if((u32)Query(&iface)!=0 || !iface) return -3;
  fprintf(stderr,"[5955] WbioQueryEngineInterface returned a non-null interface\n");
  /* Read-only interface reconnaissance. Never invoke a vtable slot.
   * The returned pointer must lie inside this guarded PE image and have
   * enough room for the bounded 0x20-byte header and 41 pointer slots. */
  {
    const uintptr_t base=(uintptr_t)g_image;
    const uintptr_t addr=(uintptr_t)iface;
    const size_t inspect_bytes=0x20u+41u*sizeof(uint64_t);
    if (!base || addr<base || addr-base>g_layout.image_size ||
        inspect_bytes>g_layout.image_size-(addr-base)) {
      fprintf(stderr,"[5955] BLOCKED: interface outside guarded PE image\n");
      return -4;
    }
    const unsigned char *bytes=(const unsigned char *)iface;
    /* WINBIO_ENGINE_INTERFACE, Windows x64:
     * Version = two USHORTs at +0; Type = ULONG at +4;
     * Size = SIZE_T at +8; AdapterId GUID at +0x10;
     * function pointers begin at +0x20. */
    uint64_t declared_size=0;
    uint32_t interface_type=0;
    uint16_t major=0,minor=0;
    memcpy(&major,bytes,2);
    memcpy(&minor,bytes+2,2);
    memcpy(&interface_type,bytes+4,4);
    memcpy(&declared_size,bytes+8,8);
    fprintf(stderr,"[5955] interface offset=%#lx; header: Size=%llu Version=%u.%u Type=%u\n",
            (unsigned long)(addr-base),(unsigned long long)declared_size,
            major,minor,interface_type);
    if(declared_size<0x20u || declared_size>4096u ||
       declared_size>g_layout.image_size-(addr-base)) {
      fprintf(stderr,"[5955] BLOCKED: implausible interface Size\n");
      return -5;
    }
    if(declared_size != inspect_bytes) {
      fprintf(stderr,"[5955] BLOCKED: unexpected interface size; expected %zu bytes\n",inspect_bytes);
      return -6;
    }
    unsigned good=0;
    for(unsigned i=0;i<41u;i++){
      uint64_t fn=0;
      memcpy(&fn,bytes+0x20u+8u*i,8);
      int executable=0;
      if(fn>=base && fn-base<g_layout.image_size) {
        const uint64_t rva=fn-base;
        for(unsigned j=0;j<g_layout.section_count;j++){
          const uint64_t at=g_layout.section_table+(uint64_t)j*40u;
          const uint32_t vsize=f32(at+8),sec_rva=f32(at+12);
          const uint32_t rawsize=f32(at+16),flags=f32(at+36);
          const uint64_t span=vsize>rawsize?vsize:rawsize;
          if(rva>=sec_rva && rva-sec_rva<span &&
             (flags&0x20000000u)) {executable=1;break;}
        }
      }
      if(executable) {
        good++;
        fprintf(stderr,"[5955] interface slot[%02u] +%#x: image+%#lx EXECUTABLE\n",
                i,0x20u+8u*i,(unsigned long)(fn-base));
      } else {
        fprintf(stderr,"[5955] interface slot[%02u] +%#x: INVALID/NOT_EXECUTABLE\n",
                i,0x20u+8u*i);
      }
    }
    fprintf(stderr,"[5955] executable interface pointers: %u/41\n",good);
    if(good!=41u) {
      fprintf(stderr,"[5955] BLOCKED: unverified interface pointers\n");
      return -7;
    }
  }
  return 0;
#endif /* FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT */
}

int ft_engine_open(const char *dll_path){
#if !defined(FT5955_ALLOW_UNVERIFIED_ATTACH) || !defined(FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT)
  (void)dll_path;
  fprintf(stderr,"[5955] BLOCKED: 9201 Attach ABI not verified for the MOH 5955 engine\n");
  return -100;
#else
  /* Re-arm the %gs TEB on re-open: arch_prctl is per-thread and fprintd
   * re-opens the device (often on a different thread) between operations. */
  if(g_loaded){ return set_engine_gs_current()==0 ? 0 : -1; }
  g_dllpath = dll_path ? dll_path : "ftWbioEngineAdapter.dll";
  register_shims();
  if(load_pe()!=0) return -1;
  void *q=get_export("WbioQueryEngineInterface");
  if(!q) return -2;
  u64 (MS *Query)(void**)=q;
  void *iface=0;
  if((u32)Query(&iface)!=0 || !iface) return -3;
  g_iface=iface;
  memset(&pipeline,0,sizeof pipeline);
  pipeline.engine_handle=(void *)(uintptr_t)UINT64_MAX;
  build_storage_vtable();
  pipeline.sensor_interface=&g_sensor_vt;
  pipeline.engine_interface=iface;
  pipeline.storage_interface=&g_storage_vt;
  u64 (MS *Attach)(void*)=*(void**)((u8*)iface+32+0*8);
  if((u32)Attach(&pipeline)!=0) return -4;
  /* The old FT9201-specific writes to context +0x24/+0x28 are removed.
   * Their 5955 meaning is NOT established by the Attach disassembly.
   * Context validation and method-specific sensor/storage callbacks remain
   * prerequisites before this path may be enabled. */
  if(!pipeline.engine_context) return -5;
  g_loaded=1;
  return 0;
#endif /* FT5955_ALLOW_UNVERIFIED_ATTACH */
}

void ft_engine_close(void){
  /* The engine maps at a fixed base and is loaded once per process; a libfprint
   * device close/reopen must NOT tear it down (and must not clear g_iface, or the
   * next open — which short-circuits on the load-once guard — leaves a null
   * interface and the following engine call segfaults). Intentional no-op. */
}

uint32_t ft_engine_accept(const uint8_t *img,int sw,int sh,uint8_t purpose){
  if(set_engine_gs_current()!=0) return UINT32_MAX; /* fail closed */
  prepare_frame((const u8*)img, sw, sh);
  int total=build_bir(small, ENG_W, ENG_H);
  u32 rej=0;
  u64 (MS *Accept)(void*,void*,u64,u64,void*)=*(void**)((u8*)g_iface+32+8*8);
  return (u32)Accept(&pipeline, birbuf, total, purpose, &rej);
}

int ft_engine_enroll_begin(void){
  if(set_engine_gs_current()!=0) return -1;
  g_have_record=0; g_rec_tsize=0;
  u64 (MS *Create)(void*)=*(void**)((u8*)g_iface+32+12*8);
  u32 hr=(u32)Create(&pipeline);
  fprintf(stderr,"[5955] ENROLL_DIAG create_hr=0x%08x\n",hr);
  return hr==0?0:-2;
}

int ft_engine_enroll_update(void){
  if(set_engine_gs_current()!=0) return -1;
  u64 (MS *Update)(void*,void*)=*(void**)((u8*)g_iface+32+13*8);
  u64 (MS *Status)(void*,void*)=*(void**)((u8*)g_iface+32+14*8);
  u32 urej=0; u64 uhr=Update(&pipeline,&urej);
  fprintf(stderr,"[5955] ENROLL_DIAG update_hr=0x%08x update_reject=%u\n",
          (u32)uhr,urej);
  if((u32)uhr==0x80098008u) return 2; /* WINBIO_E_BAD_CAPTURE */
  if(((u32)uhr & 0x80000000u)!=0) return -2; /* unexpected failure */
  if(urej) return 2;
  u32 srej=0; u64 shr=Status(&pipeline,&srej);
  fprintf(stderr,"[5955] ENROLL_DIAG status_hr=0x%08x status_reject=%u\n",
          (u32)shr,srej);
  if((u32)shr==0) return 0;           /* S_OK: ready to commit */
  if((u32)shr==0x00090001u) return 1; /* WINBIO_I_MORE_DATA */
  if((u32)shr==0x80098008u || srej) return 2; /* rejected */
  return -3; /* unrecognised status: NOT proof more data needed */
}

static void fill_identity(u8 *id){ memset(id,0,76); *(u32*)id=3; for(int i=0;i<16;i++) id[8+i]=0xA0+i; }

int ft_engine_enroll_commit(uint8_t **out,size_t *outlen){
  if(set_engine_gs_current()!=0) return -1;
  u8 id[76]; fill_identity(id);
  g_have_record=0;
  u64 (MS *Commit)(void*,void*,u8)=*(void**)((u8*)g_iface+32+17*8);
  if((u32)Commit(&pipeline,id,1)!=0 || !g_have_record) return -1;
  *out=malloc(g_rec_tsize); if(!*out) return -2;
  memcpy(*out, g_rec_template, g_rec_tsize); *outlen=g_rec_tsize;
  return 0;
}

int ft_engine_verify(const uint8_t *tmpl,size_t tmpllen){
  if(set_engine_gs_current()!=0) return 0;
  if(tmpllen==0 || tmpllen>sizeof g_rec_template) return 0;
  memcpy(g_rec_template, tmpl, tmpllen); g_rec_tsize=tmpllen; g_have_record=1;
  u8 id[76]; fill_identity(id);
  u8 m=0; u32 ps=0,hs=0,vr=0; void*plp=0,*hp=0;
  u64 (MS *Verify)(void*,void*,u8,void*,void*,void*,void*,void*,void*)=*(void**)((u8*)g_iface+32+10*8);
  Verify(&pipeline, id, 1, &m, &ps, &plp, &hs, &hp, &vr);
  return m?1:0;
}
