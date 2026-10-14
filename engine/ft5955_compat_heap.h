/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Minimal tracked Windows process heap for the isolated x64 MOH bridge.
 * The Win32 heap is independent from host malloc-owned allocations.
 */
#ifndef FT5955_COMPAT_HEAP_H
#define FT5955_COMPAT_HEAP_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_HEAP_MS __attribute__((ms_abi))
#else
#error The experimental MOH bridge requires x86-64 GCC or Clang
#endif
#define FT5955_HEAP_ZERO_MEMORY 8u
#define FT5955_HEAP_REALLOC_IN_PLACE_ONLY 16u
void *FT5955_HEAP_MS ft5955_GetProcessHeap(void);
void *FT5955_HEAP_MS ft5955_HeapAlloc(void *heap, uint32_t flags, uint64_t bytes);
int FT5955_HEAP_MS ft5955_HeapFree(void *heap, uint32_t flags, void *block);
void *FT5955_HEAP_MS ft5955_HeapReAlloc(void *heap, uint32_t flags,
                                        void *block, uint64_t bytes);
uint64_t FT5955_HEAP_MS ft5955_HeapSize(void *heap, uint32_t flags,
                                        const void *block);
int FT5955_HEAP_MS ft5955_HeapValidate(void *heap, uint32_t flags,
                                       const void *block);
int FT5955_HEAP_MS ft5955_HeapQueryInformation(void *heap, int info_class,
    void *buffer, uint64_t buffer_size, uint64_t *return_length);
#endif
