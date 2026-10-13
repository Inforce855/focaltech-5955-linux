/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_compat_compare.h"
#include "ft5955_compat_locale.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main(void)
{
    const uint16_t cat[] = {'c','a','t',0};
    const uint16_t cat2[] = {'c','a','t',0};
    const uint16_t car[] = {'c','a','r',0};
    const uint16_t cats[] = {'c','a','t','s',0};
    const uint16_t upper[] = {'C','A','T',0};
    const uint16_t nonascii[] = {'c',0x00e9,0};
    const uint16_t early_nonascii[] = {'a',0x00e9,0};
    const uint16_t invalid[] = {'\n',0};

    assert(ft5955_CompareStringW(FT5955_LCID_EN_GB, 0, cat, -1, cat2, -1) == 2);
    assert(ft5955_CompareStringW(FT5955_LCID_EN_GB, 0, car, -1, cat, -1) == 1);
    assert(ft5955_CompareStringW(FT5955_LCID_EN_US, 0, cat, -1, car, -1) == 3);
    assert(ft5955_CompareStringW(FT5955_LCID_INVARIANT, 0, cat, -1, cats, -1) == 1);
    assert(ft5955_CompareStringW(FT5955_LCID_EN_GB, 1, cat, -1, upper, -1) == 2);
    assert(ft5955_CompareStringW(FT5955_LCID_EN_GB, 1, cat, 3, cats, 3) == 2);
    assert(!ft5955_CompareStringW(FT5955_LCID_EN_GB, 0, cat, 0, car, -1));
    assert(!ft5955_CompareStringW(0x040c, 0, cat, -1, car, -1));
    assert(!ft5955_CompareStringW(FT5955_LCID_EN_GB, 2, cat, -1, car, -1));
    assert(!ft5955_CompareStringW(FT5955_LCID_EN_GB, 0, cat, -2, car, -1));
    assert(!ft5955_CompareStringW(FT5955_LCID_EN_GB, 0, NULL, -1, car, -1));
    assert(!ft5955_CompareStringW(FT5955_LCID_EN_GB, 0, cat, -1, nonascii, -1));
    assert(!ft5955_CompareStringW(FT5955_LCID_EN_GB, 0, early_nonascii, -1, cat, -1));
    assert(!ft5955_CompareStringW(FT5955_LCID_EN_GB, 0, cat, -1, invalid, -1));
    puts("5955 bounded CompareStringW: synthetic tests OK");
    return 0;
}
