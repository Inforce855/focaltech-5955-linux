/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Experimental, restricted Windows process-heap emulation.
 *
 * Explicit metadata prevents treating a foreign or double-freed pointer
 * as a valid allocation. All metadata operations are mutex-serialised.
 * We NEVER free an untracked pointer. Blocks are 16-byte aligned as
 * required by the Windows x64 heap ABI. We support only the process
 * heap; no private HeapCreate heaps, LFH or exception generation.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_heap.h"
#include "ft5955_compat_error.h"
#include <pthread.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

enum { ERROR_INVALID_HANDLE = 6, ERROR_INVALID_PARAMETER = 87 };
static char process_heap_token;
struct block_record {
    void *pointer;
    uint64_t requested;
    uint64_t capacity;
    struct block_record *next;
};
static pthread_mutex_t heap_lock = PTHREAD_MUTEX_INITIALIZER;
static struct block_record *blocks;

static int valid_heap(void *heap)
{
    return heap == (void *)&process_heap_token;
}
static struct block_record **find_record(const void *p)
{
    struct block_record **link = &blocks;
    while (*link && (*link)->pointer != p)
        link = &(*link)->next;
    return link;
}
static void *aligned_alloc_block(uint64_t size)
{
    if (size > SIZE_MAX) return NULL;
    void *memory = NULL;
    if (posix_memalign(&memory, 16, (size_t)(size ? size : 1)) != 0)
        return NULL;
    return memory;
}
static int alloc_flags(uint32_t f)
{
    /* HEAP_NO_SERIALIZE is forbidden with process heap; exception generation
     * is not emulated and must not silently become a NULL return. */
    return f == 0u || f == FT5955_HEAP_ZERO_MEMORY;
}
static int realloc_flags(uint32_t f)
{
    return (f & ~(FT5955_HEAP_ZERO_MEMORY |
                  FT5955_HEAP_REALLOC_IN_PLACE_ONLY)) == 0;
}
void *FT5955_HEAP_MS ft5955_GetProcessHeap(void)
{
    return &process_heap_token;
}
void *FT5955_HEAP_MS ft5955_HeapAlloc(void *heap, uint32_t flags, uint64_t size)
{
    if (!valid_heap(heap) || !alloc_flags(flags)) return NULL;
    void *memory = aligned_alloc_block(size);
    if (!memory) return NULL;
    struct block_record *record = malloc(sizeof *record);
    if (!record) { free(memory); return NULL; }
    if (flags & FT5955_HEAP_ZERO_MEMORY)
        memset(memory, 0, (size_t)size);
    *record = (struct block_record){ memory, size, size ? size : 1, NULL };
    pthread_mutex_lock(&heap_lock);
    record->next = blocks;
    blocks = record;
    pthread_mutex_unlock(&heap_lock);
    return memory;
}
int FT5955_HEAP_MS ft5955_HeapFree(void *heap, uint32_t flags, void *memory)
{
    if (!valid_heap(heap)) {
        ft5955_SetLastError(ERROR_INVALID_HANDLE); return 0;
    }
    if (flags) {
        ft5955_SetLastError(ERROR_INVALID_PARAMETER); return 0;
    }
    if (!memory) return 1; /* Windows documents lpMem as optional. */
    pthread_mutex_lock(&heap_lock);
    struct block_record **link = find_record(memory);
    struct block_record *record = *link;
    if (!record) {
        pthread_mutex_unlock(&heap_lock);
        ft5955_SetLastError(ERROR_INVALID_PARAMETER); return 0;
    }
    *link = record->next;
    free(record->pointer);
    free(record);
    pthread_mutex_unlock(&heap_lock);
    return 1;
}
void *FT5955_HEAP_MS ft5955_HeapReAlloc(void *heap, uint32_t flags,
                                        void *memory, uint64_t size)
{
    /* Per Microsoft, HeapReAlloc requires a block from HeapAlloc; on
     * failure neither block nor Windows last-error value is changed. */
    if (!valid_heap(heap) || !memory || !realloc_flags(flags))
        return NULL;
    pthread_mutex_lock(&heap_lock);
    struct block_record *record = *find_record(memory);
    if (!record) {
        pthread_mutex_unlock(&heap_lock);
        return NULL;
    }
    if (size <= record->capacity) {
        if ((flags & FT5955_HEAP_ZERO_MEMORY) && size > record->requested)
            memset((unsigned char *)memory + (size_t)record->requested,
                   0, (size_t)(size - record->requested));
        record->requested = size;
        pthread_mutex_unlock(&heap_lock);
        return memory;
    }
    if (flags & FT5955_HEAP_REALLOC_IN_PLACE_ONLY) {
        pthread_mutex_unlock(&heap_lock);
        return NULL;
    }
    void *replacement = aligned_alloc_block(size);
    if (!replacement) {
        pthread_mutex_unlock(&heap_lock);
        return NULL;
    }
    memcpy(replacement, memory, (size_t)record->requested);
    if (flags & FT5955_HEAP_ZERO_MEMORY)
        memset((unsigned char *)replacement + (size_t)record->requested,
               0, (size_t)(size-record->requested));
    free(record->pointer);
    record->pointer = replacement;
    record->requested = size;
    record->capacity = size;
    pthread_mutex_unlock(&heap_lock);
    return replacement;
}
uint64_t FT5955_HEAP_MS ft5955_HeapSize(void *heap, uint32_t flags,
                                        const void *memory)
{
    if (!valid_heap(heap) || flags || !memory) return UINT64_MAX;
    pthread_mutex_lock(&heap_lock);
    struct block_record *record = *find_record(memory);
    uint64_t size = record ? record->requested : UINT64_MAX;
    pthread_mutex_unlock(&heap_lock);
    return size;
}
int FT5955_HEAP_MS ft5955_HeapValidate(void *heap, uint32_t flags,
                                       const void *memory)
{
    /* HeapValidate never sets GetLastError. */
    if (!valid_heap(heap) || flags) return 0;
    pthread_mutex_lock(&heap_lock);
    int valid = !memory || (*find_record(memory) != NULL);
    pthread_mutex_unlock(&heap_lock);
    return valid;
}
int FT5955_HEAP_MS ft5955_HeapQueryInformation(void *heap, int info_class,
    void *buffer, uint64_t length, uint64_t *return_length)
{
    if (!valid_heap(heap)) {
        ft5955_SetLastError(ERROR_INVALID_HANDLE); return 0;
    }
    /* Only HeapCompatibilityInformation=0 (standard heap) is modelled. */
    if (info_class != 0) {
        ft5955_SetLastError(ERROR_INVALID_PARAMETER); return 0;
    }
    if (return_length) *return_length = sizeof(uint32_t);
    if (!buffer || length < sizeof(uint32_t)) {
        ft5955_SetLastError(ERROR_INVALID_PARAMETER); return 0;
    }
    const uint32_t standard_heap = 0;
    memcpy(buffer, &standard_heap, sizeof standard_heap);
    return 1;
}
