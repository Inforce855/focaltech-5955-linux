/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Experimental pthread-backed Win32 CRITICAL_SECTION compatibility.
 * Does not emulate direct reads of the Windows CRITICAL_SECTION fields.
 */
#ifndef FT5955_COMPAT_CS_H
#define FT5955_COMPAT_CS_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_CS_MS __attribute__((ms_abi))
#else
#error FT5955 bridge requires x86-64 GCC or Clang
#endif
void FT5955_CS_MS ft5955_InitializeCriticalSection(void *cs);
int FT5955_CS_MS ft5955_InitializeCriticalSectionAndSpinCount(void *cs, uint32_t spin_count);
void FT5955_CS_MS ft5955_EnterCriticalSection(void *cs);
void FT5955_CS_MS ft5955_LeaveCriticalSection(void *cs);
void FT5955_CS_MS ft5955_DeleteCriticalSection(void *cs);
#endif
