/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Offline test, no PE loading, USB, fprintd or biometric data.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_error.h"
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>

static pthread_barrier_t ready;
static void *worker(void *arg)
{
    uint32_t own_error = (uint32_t)(uintptr_t)arg;
    assert(ft5955_GetLastError() == 0u);
    ft5955_SetLastError(own_error);
    int status = pthread_barrier_wait(&ready);
    assert(status == 0 || status == PTHREAD_BARRIER_SERIAL_THREAD);
    for (int i = 0; i < 10000; ++i)
        assert(ft5955_GetLastError() == own_error);
    return NULL;
}
int main(void)
{
    assert(ft5955_GetLastError() == 0u);
    ft5955_SetLastError(1234u);
    assert(ft5955_GetLastError() == 1234u);
    assert(pthread_barrier_init(&ready, NULL, 3) == 0);
    pthread_t workers[2];
    assert(pthread_create(&workers[0], NULL, worker, (void *)(uintptr_t)4321u) == 0);
    assert(pthread_create(&workers[1], NULL, worker, (void *)(uintptr_t)9876u) == 0);
    int status = pthread_barrier_wait(&ready);
    assert(status == 0 || status == PTHREAD_BARRIER_SERIAL_THREAD);
    assert(ft5955_GetLastError() == 1234u);
    assert(pthread_join(workers[0], NULL) == 0);
    assert(pthread_join(workers[1], NULL) == 0);
    assert(pthread_barrier_destroy(&ready) == 0);
    assert(ft5955_GetLastError() == 1234u);
    ft5955_SetLastError(0u);
    assert(ft5955_GetLastError() == 0u);
    puts("5955 Win32 thread-local last-error: synthetic tests OK");
    return 0;
}
