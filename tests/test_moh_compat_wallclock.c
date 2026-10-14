/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Verify Win32 clock shims against native Linux clocks without PE execution.
 * Return test errors instead of aborting or producing coredumps.
 */
#define _GNU_SOURCE
#include "ft5955_compat_time.h"
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static unsigned failures;
#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr,"5955 clock test line %d: %s\n", __LINE__, #expr); \
    failures++; \
} } while (0)

static uint64_t reference_filetime(const struct timespec *t)
{
    return UINT64_C(116444736000000000)
         + (uint64_t)t->tv_sec * UINT64_C(10000000)
         + (uint64_t)t->tv_nsec / 100u;
}
static uint32_t reference_ticks(const struct timespec *t)
{
    return (uint32_t)((uint64_t)t->tv_sec * UINT64_C(1000)
                     + (uint64_t)t->tv_nsec / 1000000u);
}
int main(void)
{
    struct timespec realtime_before, realtime_after;
    struct timespec uptime_before, uptime_after;
    CHECK(clock_gettime(CLOCK_REALTIME,&realtime_before)==0);
    uint64_t filetime = 0;
    ft5955_GetSystemTimeAsFileTime(&filetime);
    CHECK(clock_gettime(CLOCK_REALTIME,&realtime_after)==0);
    CHECK(filetime >= reference_filetime(&realtime_before));
    CHECK(filetime <= reference_filetime(&realtime_after) + UINT64_C(10000000));
    ft5955_GetSystemTimeAsFileTime(NULL);

    CHECK(clock_gettime(CLOCK_BOOTTIME,&uptime_before)==0);
    uint32_t ticks_before = ft5955_GetTickCount();
    CHECK(clock_gettime(CLOCK_BOOTTIME,&uptime_after)==0);
    const uint32_t lower = reference_ticks(&uptime_before);
    const uint32_t upper = reference_ticks(&uptime_after);
    /* Modular unsigned comparisons tolerate the expected 32-bit wrap. */
    CHECK((uint32_t)(ticks_before - lower) < 1000u);
    CHECK((uint32_t)(upper - ticks_before) < 1000u);

    ft5955_Sleep(3);
    uint32_t ticks_after = ft5955_GetTickCount();
    CHECK((uint32_t)(ticks_after - ticks_before) < 5000u);
    CHECK((uint32_t)(ticks_after - ticks_before) >= 2u);

    /* This is a wall-clock / boot-clock test, not a fake counter step. */
    if (failures) {
        fprintf(stderr,"5955 time compatibility: %u test failure(s)\n", failures);
        return 1;
    }
    puts("5955 real FILETIME and monotonic uptime: synthetic tests OK");
    return 0;
}
