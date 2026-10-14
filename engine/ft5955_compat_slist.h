/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Experimental x64 Windows SLIST ABI, 16-byte aligned entries and header.
 * Uses 128-bit atomic compare-exchange; link with -latomic on Linux.
 */
#ifndef FT5955_COMPAT_SLIST_H
#define FT5955_COMPAT_SLIST_H
#include <stdint.h>
#include <stddef.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_SLIST_MS __attribute__((ms_abi))
#else
#error FocalTech MOH SList requires x86-64 GCC or Clang
#endif
typedef struct __attribute__((aligned(16))) ft5955_slist_entry {
    struct ft5955_slist_entry *Next;
} ft5955_slist_entry;
typedef struct __attribute__((aligned(16))) ft5955_slist_header {
    uint64_t depth_sequence;
    uint64_t next_region;
} ft5955_slist_header;
_Static_assert(sizeof(ft5955_slist_header) == 16, "x64 SLIST_HEADER is 16 bytes");
_Static_assert(_Alignof(ft5955_slist_header) == 16, "x64 SLIST_HEADER alignment");
_Static_assert(_Alignof(ft5955_slist_entry) == 16, "x64 SLIST_ENTRY alignment");
void FT5955_SLIST_MS ft5955_InitializeSListHead(ft5955_slist_header *head);
ft5955_slist_entry *FT5955_SLIST_MS
ft5955_InterlockedPushEntrySList(ft5955_slist_header *head,
                                ft5955_slist_entry *entry);
ft5955_slist_entry *FT5955_SLIST_MS
ft5955_InterlockedFlushSList(ft5955_slist_header *head);
#endif
