/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Thread-backed Win32 FLS compatibility for non-fiber engine paths.
 */
#ifndef FT5955_COMPAT_FLS_H
#define FT5955_COMPAT_FLS_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_FLS_MS __attribute__((ms_abi))
#else
#error FT5955 engine loader requires x86-64 GCC or Clang
#endif
#define FT5955_FLS_OUT_OF_INDEXES UINT32_MAX
typedef void (FT5955_FLS_MS *ft5955_fls_callback)(void *);
uint32_t FT5955_FLS_MS ft5955_FlsAlloc(ft5955_fls_callback callback);
int FT5955_FLS_MS ft5955_FlsFree(uint32_t index);
void *FT5955_FLS_MS ft5955_FlsGetValue(uint32_t index);
int FT5955_FLS_MS ft5955_FlsSetValue(uint32_t index, void *value);
#endif
