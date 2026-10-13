/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Offline per-thread TEB/PEB x64 layout test with actual Linux stack bounds.
 * Does NOT install GS, execute Windows DLL code or touch fingerprint files.
 */
#include "ft5955_compat_teb_layout.h"
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uintptr_t load_ptr(const uint8_t *base, size_t at)
{
    uintptr_t value;
    memcpy(&value, base + at, sizeof value);
    return value;
}
static uint32_t load_u32(const uint8_t *base, size_t at)
{
    uint32_t value;
    memcpy(&value, base + at, sizeof value);
    return value;
}
static pthread_barrier_t sync_point;
static const uint8_t *teb_addresses[3];
static const uint8_t *crt_addresses[3];

static void check_current(int index)
{
    assert(ft5955_teb_prepare_current() == 0);
    const uint8_t *teb = ft5955_teb_view_current();
    volatile uint8_t marker = 7;
    assert(teb);
    uintptr_t lo = load_ptr(teb, 0x10);
    uintptr_t hi = load_ptr(teb, 0x08);
    uintptr_t sp = (uintptr_t)&marker;
    assert(lo < sp && sp < hi);
    assert(hi > lo);
    assert(load_ptr(teb, 0x30) == (uintptr_t)teb);
    assert(load_ptr(teb, 0x60) == (uintptr_t)ft5955_peb_view());
    const uint8_t *peb = ft5955_peb_view();
    const uint8_t *params = ft5955_process_parameters_view();
    assert(load_ptr(peb, 0x20) == (uintptr_t)params);
    assert(load_u32(peb, 0xbc) == 0);
    assert(load_u32(params, 0x08) == 1);
    uintptr_t slots_ptr = load_ptr(teb, 0x58);
    assert(slots_ptr != 0);
    const void *const *slots = (const void *const *)slots_ptr;
    assert(slots[0]);
    uint8_t template_byte = (uint8_t)(index + 1);
    assert(ft5955_teb_set_crt_tls_template(&template_byte, 1) == 0);
    assert(*(const uint8_t *)slots[0] == template_byte);
    assert(ft5955_teb_set_crt_tls_template(NULL, 1) == -1);
    assert(ft5955_teb_set_crt_tls_template(NULL, FT5955_CRT_TLS_BYTES + 1) == -1);
    teb_addresses[index] = teb;
    crt_addresses[index] = (const uint8_t *)slots[0];
}
static void *worker(void *arg)
{
    int index = (int)(uintptr_t)arg;
    assert(ft5955_teb_view_current() == NULL);
    check_current(index);
    int b = pthread_barrier_wait(&sync_point);
    assert(b == 0 || b == PTHREAD_BARRIER_SERIAL_THREAD);
    /* The main thread checks uniqueness before releasing worker threads. */
    b = pthread_barrier_wait(&sync_point);
    assert(b == 0 || b == PTHREAD_BARRIER_SERIAL_THREAD);
    return NULL;
}
int main(void)
{
    assert(pthread_barrier_init(&sync_point, NULL, 3) == 0);
    pthread_t a, b;
    assert(!pthread_create(&a, NULL, worker, (void *)(uintptr_t)1));
    assert(!pthread_create(&b, NULL, worker, (void *)(uintptr_t)2));
    check_current(0);
    int status = pthread_barrier_wait(&sync_point);
    assert(status == 0 || status == PTHREAD_BARRIER_SERIAL_THREAD);
    for (int i = 0; i < 3; ++i)
        for (int j = i + 1; j < 3; ++j) {
            assert(teb_addresses[i] != teb_addresses[j]);
            assert(crt_addresses[i] != crt_addresses[j]);
        }
    assert(*(const uint8_t *)crt_addresses[0] == 1);
    assert(*(const uint8_t *)crt_addresses[1] == 2);
    assert(*(const uint8_t *)crt_addresses[2] == 3);
    status = pthread_barrier_wait(&sync_point);
    assert(status == 0 || status == PTHREAD_BARRIER_SERIAL_THREAD);
    assert(!pthread_join(a, NULL));
    assert(!pthread_join(b, NULL));
    assert(!pthread_barrier_destroy(&sync_point));
    puts("5955 per-thread TEB stack bounds and PEB pointers: synthetic tests OK");
    return 0;
}
