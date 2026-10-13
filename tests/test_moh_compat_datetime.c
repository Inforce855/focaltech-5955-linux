/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_compat_datetime.h"
#include "ft5955_compat_locale.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void equals(uint16_t *utf16, const char *expected)
{
    size_t len = strlen(expected);
    for (size_t i = 0; i <= len; ++i)
        assert(utf16[i] == (unsigned char)expected[i]);
}
int main(void)
{
    const ft5955_systemtime date = {2026, 10, 0, 13, 16, 7, 8, 0};
    uint16_t out[160] = {0};
    static const uint16_t custom[] = {'d', 'd', 0};
    int n;
    n = ft5955_GetDateFormatW(FT5955_LCID_EN_GB, 0, &date, NULL, out, 160);
    assert(n == 11); equals(out, "13/10/2026");
    assert(ft5955_GetDateFormatW(FT5955_LCID_EN_GB, 0, &date, NULL, NULL, 0) == n);
    assert(!ft5955_GetDateFormatW(FT5955_LCID_EN_GB, 0, &date, NULL, out, 2));
    n = ft5955_GetDateFormatW(FT5955_LCID_EN_US, 0, &date, NULL, out, 160);
    assert(n == 11); equals(out, "10/13/2026");
    n = ft5955_GetDateFormatW(FT5955_LCID_EN_US, 2, &date, NULL, out, 160);
    assert(n > 0); equals(out, "Tuesday, October 13, 2026");
    n = ft5955_GetTimeFormatW(FT5955_LCID_EN_GB, 0, &date, NULL, out, 160);
    assert(n == 9); equals(out, "16:07:08");
    n = ft5955_GetTimeFormatW(FT5955_LCID_EN_US, 0, &date, NULL, out, 160);
    assert(n == 11); equals(out, "4:07:08 PM");
    n = ft5955_GetTimeFormatW(FT5955_LCID_EN_US, 8, &date, NULL, out, 160);
    assert(n == 9); equals(out, "16:07:08");
    assert(!ft5955_GetTimeFormatW(0x040c, 0, &date, NULL, out, 160));
    assert(!ft5955_GetTimeFormatW(FT5955_LCID_EN_GB, 0x8000, &date, NULL, out, 160));
    assert(!ft5955_GetDateFormatW(FT5955_LCID_EN_GB, 0, &date, custom, out, 160));
    const ft5955_systemtime invalid = {2026, 2, 0, 30, 0, 0, 0, 0};
    assert(!ft5955_GetDateFormatW(FT5955_LCID_EN_GB, 0, &invalid, NULL, out, 160));
    puts("5955 default date/time shims: synthetic tests OK");
    return 0;
}
