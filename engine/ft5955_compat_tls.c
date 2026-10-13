/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Windows TLS indices are global; values are separate for each thread.
 * Uses a single pthread TLS key holding an indexed per-thread array. Each
 * allocation increments the index generation, preventing stale values from
 * leaking if an index is freed and reused by a different caller/thread.
 * TlsFree deliberately does not invoke callbacks (unlike FlsFree).
 * This only implements imported Win32 TLS APIs, not TLS directly accessed via
 * the Windows TEB or fiber-local storage.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_tls.h"
#include "ft5955_compat_error.h"
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>

#define FT5955_ERROR_INVALID_PARAMETER 87u
#define FT5955_ERROR_NOT_ENOUGH_MEMORY 8u

struct index_slot {
    uint64_t generation;
    int allocated;
};
struct thread_slots {
    void *values[FT5955_TLS_CAPACITY];
    uint64_t generations[FT5955_TLS_CAPACITY];
};
static struct index_slot indices[FT5955_TLS_CAPACITY];
static pthread_mutex_t index_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_once_t key_once = PTHREAD_ONCE_INIT;
static pthread_key_t thread_key;
static int key_ready;

static void make_key(void)
{
    if (pthread_key_create(&thread_key, free) == 0)
        key_ready = 1;
}
static struct thread_slots *get_thread_slots(int create)
{
    if (pthread_once(&key_once, make_key) != 0 || !key_ready)
        return NULL;
    struct thread_slots *slots = pthread_getspecific(thread_key);
    if (!slots && create) {
        slots = calloc(1, sizeof(*slots));
        if (!slots)
            return NULL;
        if (pthread_setspecific(thread_key, slots) != 0) {
            free(slots);
            return NULL;
        }
    }
    return slots;
}

uint32_t FT5955_TLS_MS ft5955_TlsAlloc(void)
{
    if (pthread_once(&key_once, make_key) != 0 || !key_ready) {
        ft5955_SetLastError(FT5955_ERROR_NOT_ENOUGH_MEMORY);
        return FT5955_TLS_OUT_OF_INDEXES;
    }
    pthread_mutex_lock(&index_lock);
    for (uint32_t i = 0; i < FT5955_TLS_CAPACITY; ++i) {
        if (!indices[i].allocated) {
            indices[i].allocated = 1;
            if (++indices[i].generation == 0)
                indices[i].generation = 1;
            pthread_mutex_unlock(&index_lock);
            return i;
        }
    }
    pthread_mutex_unlock(&index_lock);
    ft5955_SetLastError(FT5955_ERROR_NOT_ENOUGH_MEMORY);
    return FT5955_TLS_OUT_OF_INDEXES;
}

int FT5955_TLS_MS ft5955_TlsFree(uint32_t index)
{
    pthread_mutex_lock(&index_lock);
    if (index >= FT5955_TLS_CAPACITY || !indices[index].allocated) {
        pthread_mutex_unlock(&index_lock);
        ft5955_SetLastError(FT5955_ERROR_INVALID_PARAMETER);
        return 0;
    }
    indices[index].allocated = 0;
    pthread_mutex_unlock(&index_lock);
    return 1;
}

void *FT5955_TLS_MS ft5955_TlsGetValue(uint32_t index)
{
    struct thread_slots *thread = get_thread_slots(0);
    void *value = NULL;
    pthread_mutex_lock(&index_lock);
    if (index >= FT5955_TLS_CAPACITY || !indices[index].allocated) {
        pthread_mutex_unlock(&index_lock);
        ft5955_SetLastError(FT5955_ERROR_INVALID_PARAMETER);
        return NULL;
    }
    if (thread && thread->generations[index] == indices[index].generation)
        value = thread->values[index];
    pthread_mutex_unlock(&index_lock);
    /* A valid slot holding NULL is success, not an error. */
    ft5955_SetLastError(0);
    return value;
}

int FT5955_TLS_MS ft5955_TlsSetValue(uint32_t index, void *value)
{
    pthread_mutex_lock(&index_lock);
    if (index >= FT5955_TLS_CAPACITY || !indices[index].allocated) {
        pthread_mutex_unlock(&index_lock);
        ft5955_SetLastError(FT5955_ERROR_INVALID_PARAMETER);
        return 0;
    }
    /* Keep the index mutex locked across value assignment so concurrent
     * TlsFree + TlsAlloc cannot insert a stale generation into a reused slot. */
    struct thread_slots *thread = get_thread_slots(1);
    if (!thread) {
        pthread_mutex_unlock(&index_lock);
        ft5955_SetLastError(FT5955_ERROR_NOT_ENOUGH_MEMORY);
        return 0;
    }
    thread->values[index] = value;
    thread->generations[index] = indices[index].generation;
    pthread_mutex_unlock(&index_lock);
    return 1;
}
