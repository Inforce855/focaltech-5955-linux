/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Small Win32 time/thread/console compatibility surface for the 5955 engine.
 */
#ifndef FT5955_COMPAT_TIME_H
#define FT5955_COMPAT_TIME_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_MS_ABI __attribute__((ms_abi))
#else
#error This compatibility bridge currently requires x86-64 GCC/Clang
#endif

typedef struct {
    uint16_t year, month, day_of_week, day;
    uint16_t hour, minute, second, milliseconds;
} ft5955_systemtime;

int FT5955_MS_ABI ft5955_QueryPerformanceFrequency(int64_t *frequency);
int FT5955_MS_ABI ft5955_QueryPerformanceCounter(int64_t *counter);
void FT5955_MS_ABI ft5955_Sleep(uint32_t milliseconds);
void FT5955_MS_ABI ft5955_GetLocalTime(ft5955_systemtime *out);
void *FT5955_MS_ABI ft5955_GetCurrentThread(void);
uint32_t FT5955_MS_ABI ft5955_GetConsoleOutputCP(void);
#endif
