/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Windows Fiber Local Storage shim using POSIX per-thread storage.
 * Supports native threads and Win32 callback cleanup at thread exit/Free;
 * DOES NOT implement multiple Windows fibers within a single pthread.
 * This limitation requires validation before enabling engine Attach.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_fls.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>

#define FT5955_FLS_LIMIT 128
struct fls_slot {
    int in_use;
    uint64_t generation;
    ft5955_fls_callback callback;
};
struct fls_thread {
    struct fls_thread *next;
    void *values[FT5955_FLS_LIMIT];
    uint64_t generations[FT5955_FLS_LIMIT];
};
struct callback_job {
    ft5955_fls_callback function;
    void *value;
};
static struct fls_slot slots[FT5955_FLS_LIMIT];
static struct fls_thread *threads;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_once_t once = PTHREAD_ONCE_INIT;
static pthread_key_t key;
static int key_ok;

static void fls_thread_destroy(void *pointer)
{
    struct fls_thread *thread = pointer;
    struct callback_job jobs[FT5955_FLS_LIMIT];
    size_t count = 0;
    pthread_mutex_lock(&lock);
    struct fls_thread **p = &threads;
    while (*p && *p != thread)
        p = &(*p)->next;
    if (*p == thread)
        *p = thread->next;
    for (size_t i = 0; i < FT5955_FLS_LIMIT; ++i) {
        if (slots[i].in_use && slots[i].callback && thread->values[i] &&
            slots[i].generation == thread->generations[i]) {
            jobs[count++] = (struct callback_job){slots[i].callback, thread->values[i]};
        }
    }
    pthread_mutex_unlock(&lock);
    free(thread);
    for (size_t i = 0; i < count; ++i)
        jobs[i].function(jobs[i].value);
}

static void fls_init(void)
{
    if (pthread_key_create(&key, fls_thread_destroy) == 0)
        key_ok = 1;
}

static struct fls_thread *get_thread(int create)
{
    pthread_once(&once, fls_init);
    if (!key_ok)
        return NULL;
    struct fls_thread *thread = pthread_getspecific(key);
    if (!thread && create) {
        thread = calloc(1, sizeof(*thread));
        if (!thread)
            return NULL;
        if (pthread_setspecific(key, thread) != 0) {
            free(thread);
            return NULL;
        }
        pthread_mutex_lock(&lock);
        thread->next = threads;
        threads = thread;
        pthread_mutex_unlock(&lock);
    }
    return thread;
}

uint32_t FT5955_FLS_MS ft5955_FlsAlloc(ft5955_fls_callback callback)
{
    pthread_once(&once, fls_init);
    if (!key_ok)
        return FT5955_FLS_OUT_OF_INDEXES;
    uint32_t found = FT5955_FLS_OUT_OF_INDEXES;
    pthread_mutex_lock(&lock);
    for (uint32_t i = 0; i < FT5955_FLS_LIMIT; ++i) {
        if (!slots[i].in_use) {
            slots[i].in_use = 1;
            slots[i].generation++;
            slots[i].callback = callback;
            found = i;
            break;
        }
    }
    pthread_mutex_unlock(&lock);
    return found;
}

void *FT5955_FLS_MS ft5955_FlsGetValue(uint32_t index)
{
    if (index >= FT5955_FLS_LIMIT)
        return NULL;
    struct fls_thread *thread = get_thread(0);
    void *value = NULL;
    pthread_mutex_lock(&lock);
    if (slots[index].in_use && thread &&
        slots[index].generation == thread->generations[index])
        value = thread->values[index];
    pthread_mutex_unlock(&lock);
    return value;
}

int FT5955_FLS_MS ft5955_FlsSetValue(uint32_t index, void *value)
{
    if (index >= FT5955_FLS_LIMIT)
        return 0;
    struct fls_thread *thread = get_thread(1);
    if (!thread)
        return 0;
    int success = 0;
    pthread_mutex_lock(&lock);
    if (slots[index].in_use) {
        thread->values[index] = value;
        thread->generations[index] = slots[index].generation;
        success = 1;
    }
    pthread_mutex_unlock(&lock);
    return success;
}

int FT5955_FLS_MS ft5955_FlsFree(uint32_t index)
{
    if (index >= FT5955_FLS_LIMIT)
        return 0;
    pthread_mutex_lock(&lock);
    if (!slots[index].in_use) {
        pthread_mutex_unlock(&lock);
        return 0;
    }
    size_t count = 0;
    for (struct fls_thread *t = threads; t; t = t->next)
        if (t->values[index] && t->generations[index] == slots[index].generation &&
            slots[index].callback)
            ++count;
    struct callback_job *jobs = count ? calloc(count, sizeof(*jobs)) : NULL;
    if (count && !jobs) {
        pthread_mutex_unlock(&lock);
        return 0;
    }
    size_t n = 0;
    for (struct fls_thread *t = threads; t; t = t->next) {
        if (t->values[index] && t->generations[index] == slots[index].generation &&
            slots[index].callback)
            jobs[n++] = (struct callback_job){slots[index].callback, t->values[index]};
        t->values[index] = NULL;
        t->generations[index] = 0;
    }
    slots[index].in_use = 0;
    slots[index].callback = NULL;
    pthread_mutex_unlock(&lock);
    for (size_t i = 0; i < n; ++i)
        jobs[i].function(jobs[i].value);
    free(jobs);
    return 1;
}
