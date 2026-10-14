/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_compat_time.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {
    int64_t frequency = 0, before = 0, after = 0;
    ft5955_systemtime now = {0};
    assert(ft5955_QueryPerformanceFrequency(&frequency) == 1);
    assert(frequency == 1000000000LL);
    assert(ft5955_QueryPerformanceFrequency(NULL) == 0);
    assert(ft5955_QueryPerformanceCounter(&before) == 1);
    ft5955_Sleep(2);
    assert(ft5955_QueryPerformanceCounter(&after) == 1);
    assert(after > before);
    assert(after - before < frequency * 5);
    ft5955_GetLocalTime(&now);
    assert(now.year >= 2020 && now.year < 2100);
    assert(now.month >= 1 && now.month <= 12);
    assert(now.day >= 1 && now.day <= 31);
    assert(now.day_of_week <= 6);
    assert(now.hour <= 23);
    assert(now.minute <= 59);
    assert(now.second <= 60);
    assert(now.milliseconds <= 999);
    assert(ft5955_GetCurrentThread() == (void *)(intptr_t)-2);
    assert(ft5955_GetConsoleOutputCP() == 437);
    puts("5955 time/thread shims: synthetic tests OK");
    return 0;
}
