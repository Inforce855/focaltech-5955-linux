/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Correctly typed, narrow Win32 shims for MOH matching-engine research.
 * Does not access USB, biometric data, filesystem or Windows DLL.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_time.h"
#include <errno.h>
#include <stddef.h>
#include <time.h>

int FT5955_MS_ABI
ft5955_QueryPerformanceFrequency(int64_t *frequency)
{
    if (!frequency)
        return 0;
    *frequency = 1000000000LL; /* nanosecond monotonic clock */
    return 1;
}

int FT5955_MS_ABI
ft5955_QueryPerformanceCounter(int64_t *counter)
{
    struct timespec now;
    if (!counter || clock_gettime(CLOCK_MONOTONIC, &now) != 0)
        return 0;
    *counter = (int64_t)now.tv_sec * 1000000000LL + now.tv_nsec;
    return 1;
}

void FT5955_MS_ABI
ft5955_Sleep(uint32_t milliseconds)
{
    struct timespec remaining = {
        .tv_sec = milliseconds / 1000,
        .tv_nsec = (long)(milliseconds % 1000) * 1000000L
    };
    while (nanosleep(&remaining, &remaining) == -1 && errno == EINTR)
        ;
}

void FT5955_MS_ABI
ft5955_GetLocalTime(ft5955_systemtime *out)
{
    struct timespec now;
    struct tm local;
    if (!out || clock_gettime(CLOCK_REALTIME, &now) != 0 ||
        !localtime_r(&now.tv_sec, &local))
        return;
    out->year = (uint16_t)(local.tm_year + 1900);
    out->month = (uint16_t)(local.tm_mon + 1);
    out->day_of_week = (uint16_t)local.tm_wday;
    out->day = (uint16_t)local.tm_mday;
    out->hour = (uint16_t)local.tm_hour;
    out->minute = (uint16_t)local.tm_min;
    out->second = (uint16_t)local.tm_sec;
    out->milliseconds = (uint16_t)(now.tv_nsec / 1000000L);
}

void *FT5955_MS_ABI
ft5955_GetCurrentThread(void)
{
    return (void *)(intptr_t)-2; /* documented Windows pseudo-handle */
}

uint32_t FT5955_MS_ABI
ft5955_GetConsoleOutputCP(void)
{
    return 437; /* existing bridge's fixed OEM code page */
}
