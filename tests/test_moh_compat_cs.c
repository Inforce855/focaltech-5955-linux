/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_compat_cs.h"
#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdint.h>

static uint64_t cs_buffer[5]; /* 40-byte, 8-byte aligned Windows CS */
static int shared;
static atomic_int overlapping;
static atomic_int violations;
static void *increment_worker(void *ignored)
{
    (void)ignored;
    for (int i = 0; i < 30000; i++) {
        ft5955_EnterCriticalSection(cs_buffer);
        if (atomic_fetch_add(&overlapping, 1))
            atomic_fetch_add(&violations, 1);
        int previous = shared;
        shared = previous + 1;
        assert(atomic_fetch_sub(&overlapping, 1) == 1);
        ft5955_LeaveCriticalSection(cs_buffer);
    }
    return NULL;
}
int main(void)
{
    assert(ft5955_InitializeCriticalSectionAndSpinCount(cs_buffer, 1000));
    ft5955_EnterCriticalSection(cs_buffer);
    ft5955_EnterCriticalSection(cs_buffer); /* Windows CS must be recursive */
    ft5955_LeaveCriticalSection(cs_buffer);
    ft5955_LeaveCriticalSection(cs_buffer);
    pthread_t threads[4];
    for (int i = 0; i < 4; i++)
        assert(!pthread_create(&threads[i], NULL, increment_worker, NULL));
    for (int i = 0; i < 4; i++)
        assert(!pthread_join(threads[i], NULL));
    assert(shared == 120000);
    assert(!atomic_load(&violations));
    ft5955_DeleteCriticalSection(cs_buffer);
    ft5955_InitializeCriticalSection(cs_buffer); /* address can be reused */
    ft5955_EnterCriticalSection(cs_buffer);
    ft5955_LeaveCriticalSection(cs_buffer);
    ft5955_DeleteCriticalSection(cs_buffer);
    puts("5955 Win32 critical sections: recursive and thread-contention tests OK");
    return 0;
}
