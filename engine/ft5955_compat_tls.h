/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Per-thread Win32 TLS compatibility for the experimental MOH loader.
 */
#ifndef FT5955_COMPAT_TLS_H
#define FT5955_COMPAT_TLS_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_TLS_MS __attribute__((ms_abi))
#else
#error This experimental PE loader requires x86-64 GCC or Clang
#endif
#define FT5955_TLS_OUT_OF_INDEXES UINT32_MAX
#define FT5955_TLS_CAPACITY 1088u
uint32_t FT5955_TLS_MS ft5955_TlsAlloc(void);
int FT5955_TLS_MS ft5955_TlsFree(uint32_t index);
void *FT5955_TLS_MS ft5955_TlsGetValue(uint32_t index);
int FT5955_TLS_MS ft5955_TlsSetValue(uint32_t index, void *value);
#endif
