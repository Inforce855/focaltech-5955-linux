/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Conservative Win32 date/time formats (English defaults only).
 */
#ifndef FT5955_COMPAT_DATETIME_H
#define FT5955_COMPAT_DATETIME_H
#include "ft5955_compat_time.h"
#include <stdint.h>
int FT5955_MS_ABI ft5955_GetDateFormatW(uint32_t lcid, uint32_t flags,
    const ft5955_systemtime *date, const uint16_t *format,
    uint16_t *out, int capacity);
int FT5955_MS_ABI ft5955_GetTimeFormatW(uint32_t lcid, uint32_t flags,
    const ft5955_systemtime *time, const uint16_t *format,
    uint16_t *out, int capacity);
#endif
