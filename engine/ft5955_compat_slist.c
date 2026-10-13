/* SPDX-License-Identifier: LGPL-2.1-or-later
 * x64 SLIST push/flush for the guarded 5955 Windows MOH bridge.
 *
 * SLIST_HEADER.HeaderX64:
 * 64 low bits: Depth(16), Sequence(48)
 * 64 high bits: Reserved(4), NextEntry(60)
 *
 * With 16-byte-aligned pointers, the stored NextEntry field maps to
 * the full aligned pointer. The entire 128-bit head is updated atomically
 * with compare-exchange, avoiding an ABA race between concurrent pushes
 * and flushes. The 48-bit sequence wraps at its natural field width.
 *
 * Deliberate limits: no InterlockedPopEntrySList implementation (not an
 * import of the verified 5955 MOH DLL), no pointer reclamation/lifetime
 * management, and no support for unaligned or 32-bit callers. Reinitialising
 * a header while other threads use it is invalid. A popped/flushed chain
 * belongs to the caller. DLL execution remains explicitly disabled.
 */
#include "ft5955_compat_slist.h"
#include <stdint.h>
#include <stdio.h>

typedef unsigned __int128 atomic_word;
static const uint64_t sequence_mask = UINT64_C(0x0000ffffffffffff);

static int aligned_16(const void *pointer)
{
    return pointer && (((uintptr_t)pointer & 15u) == 0);
}
static atomic_word make_head(uint64_t depth, uint64_t sequence,
                             const ft5955_slist_entry *first)
{
    const uint64_t low=((sequence & sequence_mask) << 16)
                       | (depth & 0xffffu);
    const uint64_t high=(uint64_t)(uintptr_t)first;
    return ((atomic_word)high << 64) | low;
}
static ft5955_slist_entry *first_entry(atomic_word current)
{
    const uint64_t upper=(uint64_t)(current >> 64);
    return (ft5955_slist_entry *)(uintptr_t)(upper & ~UINT64_C(15));
}
static int reserved_clear(atomic_word current)
{
    return (((uint64_t)(current >> 64)) & 15u) == 0;
}
void FT5955_SLIST_MS ft5955_InitializeSListHead(ft5955_slist_header *head)
{
    if (!aligned_16(head)) {
        fputs("[5955 SLIST] unsupported misaligned/NULL list header\n",stderr);
        return;
    }
    __atomic_store_n((atomic_word *)head, (atomic_word)0, __ATOMIC_RELEASE);
}
ft5955_slist_entry *FT5955_SLIST_MS
ft5955_InterlockedPushEntrySList(ft5955_slist_header *head,
                                ft5955_slist_entry *entry)
{
    if (!aligned_16(head) || !aligned_16(entry)) {
        fputs("[5955 SLIST] unsupported misaligned/NULL list/entry\n",stderr);
        return NULL;
    }
    atomic_word observed=__atomic_load_n((atomic_word *)head,__ATOMIC_ACQUIRE);
    for (;;) {
        if (!reserved_clear(observed)) {
            fputs("[5955 SLIST] unrecognised SLIST_HEADER encoding\n",stderr);
            return NULL;
        }
        const uint64_t low=(uint64_t)observed;
        ft5955_slist_entry *old=first_entry(observed);
        /* SLIST_ENTRY.Next is explicitly caller-writable until publication. */
        entry->Next=old;
        uint64_t new_depth=((low & 0xffffu)+1u)&0xffffu;
        uint64_t new_sequence=((low >> 16)+1u)&sequence_mask;
        const atomic_word desired=make_head(new_depth,new_sequence,entry);
        if (__atomic_compare_exchange_n((atomic_word *)head,&observed,
                    desired,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))
            return old;
    }
}
ft5955_slist_entry *FT5955_SLIST_MS
ft5955_InterlockedFlushSList(ft5955_slist_header *head)
{
    if (!aligned_16(head)) {
        fputs("[5955 SLIST] unsupported misaligned/NULL list header\n",stderr);
        return NULL;
    }
    atomic_word observed=__atomic_load_n((atomic_word *)head,__ATOMIC_ACQUIRE);
    for (;;) {
        if (!reserved_clear(observed)) {
            fputs("[5955 SLIST] unrecognised SLIST_HEADER encoding\n",stderr);
            return NULL;
        }
        ft5955_slist_entry *old=first_entry(observed);
        if (!old) return NULL;
        uint64_t new_sequence=(((uint64_t)observed >> 16)+1u)&sequence_mask;
        const atomic_word desired=make_head(0,new_sequence,NULL);
        if (__atomic_compare_exchange_n((atomic_word *)head,&observed,
                    desired,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))
            return old;
    }
}
