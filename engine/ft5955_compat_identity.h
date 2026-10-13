/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Win32 process/thread identifiers for the experimental x64 MOH bridge.
 * Uses real Linux numeric PIDs/TIDs solely as stable local identifiers.
 * These are identifiers, not valid native Windows thread/process handles.
 */
#ifndef FT5955_COMPAT_IDENTITY_H
#define FT5955_COMPAT_IDENTITY_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_ID_MS __attribute__((ms_abi))
#else
#error FT5955 MOH bridge currently requires x86-64 GCC/Clang
#endif

uint32_t FT5955_ID_MS ft5955_GetCurrentProcessId(void);
uint32_t FT5955_ID_MS ft5955_GetCurrentThreadId(void);
#endif
