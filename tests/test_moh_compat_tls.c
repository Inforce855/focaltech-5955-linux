/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic multithreaded tests; no Windows DLL or fingerprint data.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_tls.h"
#include "ft5955_compat_error.h"
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>

static pthread_barrier_t barrier;
static uint32_t shared_index;
static void *worker(void *arg)
{
    void *my_value = arg;
    assert(ft5955_TlsGetValue(shared_index) == NULL);
    assert(ft5955_GetLastError() == 0);
    assert(ft5955_TlsSetValue(shared_index, my_value));
    int brc = pthread_barrier_wait(&barrier);
    assert(brc == 0 || brc == PTHREAD_BARRIER_SERIAL_THREAD);
    for (int i = 0; i < 10000; ++i)
        assert(ft5955_TlsGetValue(shared_index) == my_value);
    brc = pthread_barrier_wait(&barrier);
    assert(brc == 0 || brc == PTHREAD_BARRIER_SERIAL_THREAD);
    /* The main thread frees and reallocates this same global index. */
    brc = pthread_barrier_wait(&barrier);
    assert(brc == 0 || brc == PTHREAD_BARRIER_SERIAL_THREAD);
    assert(ft5955_TlsGetValue(shared_index) == NULL);
    assert(ft5955_GetLastError() == 0);
    assert(ft5955_TlsSetValue(shared_index, my_value));
    assert(ft5955_TlsGetValue(shared_index) == my_value);
    return NULL;
}
int main(void)
{
    shared_index = ft5955_TlsAlloc();
    assert(shared_index != FT5955_TLS_OUT_OF_INDEXES);
    assert(ft5955_TlsGetValue(shared_index) == NULL);
    assert(ft5955_GetLastError() == 0);
    void *main_value = (void *)(uintptr_t)0x1234;
    assert(ft5955_TlsSetValue(shared_index, main_value));
    assert(ft5955_TlsGetValue(shared_index) == main_value);
    assert(pthread_barrier_init(&barrier, NULL, 3) == 0);
    pthread_t a, b;
    assert(!pthread_create(&a, NULL, worker, (void *)(uintptr_t)0x5678));
    assert(!pthread_create(&b, NULL, worker, (void *)(uintptr_t)0x9876));
    int brc = pthread_barrier_wait(&barrier);
    assert(brc == 0 || brc == PTHREAD_BARRIER_SERIAL_THREAD);
    assert(ft5955_TlsGetValue(shared_index) == main_value);
    brc = pthread_barrier_wait(&barrier);
    assert(brc == 0 || brc == PTHREAD_BARRIER_SERIAL_THREAD);
    assert(ft5955_TlsFree(shared_index));
    uint32_t replacement = ft5955_TlsAlloc();
    assert(replacement == shared_index);
    assert(ft5955_TlsGetValue(shared_index) == NULL);
    assert(ft5955_GetLastError() == 0);
    brc = pthread_barrier_wait(&barrier);
    assert(brc == 0 || brc == PTHREAD_BARRIER_SERIAL_THREAD);
    assert(pthread_join(a, NULL) == 0);
    assert(pthread_join(b, NULL) == 0);
    assert(ft5955_TlsGetValue(shared_index) == NULL);
    assert(ft5955_TlsFree(shared_index));
    assert(!ft5955_TlsFree(shared_index));
    assert(ft5955_GetLastError() == 87);
    assert(ft5955_TlsGetValue(shared_index) == NULL);
    assert(ft5955_GetLastError() == 87);
    assert(!ft5955_TlsSetValue(shared_index, main_value));
    assert(ft5955_GetLastError() == 87);
    assert(pthread_barrier_destroy(&barrier) == 0);
    uint32_t ids[FT5955_TLS_CAPACITY];
    for (uint32_t i = 0; i < FT5955_TLS_CAPACITY; ++i) {
        ids[i] = ft5955_TlsAlloc();
        assert(ids[i] != FT5955_TLS_OUT_OF_INDEXES);
    }
    assert(ft5955_TlsAlloc() == FT5955_TLS_OUT_OF_INDEXES);
    assert(ft5955_GetLastError() == 8);
    for (uint32_t i = 0; i < FT5955_TLS_CAPACITY; ++i)
        assert(ft5955_TlsFree(ids[i]));
    puts("5955 Win32 per-thread TLS: synthetic tests OK");
    return 0;
}
