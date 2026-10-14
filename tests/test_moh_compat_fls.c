/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_compat_fls.h"
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdatomic.h>

static atomic_int callbacks;
static void FT5955_FLS_MS callback(void *value)
{
    assert(value != NULL);
    atomic_fetch_add(&callbacks, 1);
}

struct args { uint32_t index; void *value; };
static void *worker(void *arg)
{
    struct args *a = arg;
    assert(ft5955_FlsGetValue(a->index) == NULL);
    assert(ft5955_FlsSetValue(a->index, a->value));
    assert(ft5955_FlsGetValue(a->index) == a->value);
    return NULL;
}

int main(void)
{
    uint32_t index = ft5955_FlsAlloc(callback);
    assert(index != FT5955_FLS_OUT_OF_INDEXES);
    assert(ft5955_FlsSetValue(index, (void *)(uintptr_t)0x1234));
    assert(ft5955_FlsGetValue(index) == (void *)(uintptr_t)0x1234);
    struct args a = {index, (void *)(uintptr_t)0x5678};
    pthread_t t;
    assert(!pthread_create(&t, NULL, worker, &a));
    assert(!pthread_join(t, NULL));
    assert(atomic_load(&callbacks) == 1);
    assert(ft5955_FlsGetValue(index) == (void *)(uintptr_t)0x1234);
    assert(ft5955_FlsFree(index));
    assert(atomic_load(&callbacks) == 2);
    assert(!ft5955_FlsFree(index));
    assert(!ft5955_FlsSetValue(index, (void *)1));
    assert(ft5955_FlsGetValue(index) == NULL);
    uint32_t reused = ft5955_FlsAlloc(NULL);
    assert(reused == index);
    assert(ft5955_FlsGetValue(reused) == NULL);
    assert(ft5955_FlsFree(reused));
    puts("5955 FLS thread-local shims: synthetic tests OK");
    return 0;
}
