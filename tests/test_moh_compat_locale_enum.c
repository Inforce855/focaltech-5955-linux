/* SPDX-License-Identifier: LGPL-2.1-or-later */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_locale.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

static int count, stop_early, seen_us, seen_gb;
static int FT5955_LOCALE_MS callback(uint16_t *locale)
{
    const uint16_t us[] = {'0','0','0','0','0','4','0','9',0};
    const uint16_t gb[] = {'0','0','0','0','0','8','0','9',0};
    int is_us = 1, is_gb = 1;
    for (size_t i = 0; i < 9; i++) {
        if (locale[i] != us[i]) is_us = 0;
        if (locale[i] != gb[i]) is_gb = 0;
    }
    assert(is_us || is_gb);
    count++;
    seen_us += is_us;
    seen_gb += is_gb;
    return !stop_early;
}
static void reset(void) { count = stop_early = seen_us = seen_gb = 0; }

int main(void)
{
    reset();
    assert(ft5955_EnumSystemLocalesW(callback, 0));
    assert(count == 2 && seen_us == 1 && seen_gb == 1);
    reset();
    assert(ft5955_EnumSystemLocalesW(callback, FT5955_LCID_SUPPORTED));
    assert(count == 2);
    reset(); stop_early = 1;
    assert(ft5955_EnumSystemLocalesW(callback, FT5955_LCID_SUPPORTED));
    assert(count == 1);
    reset();
    assert(setenv("LC_ALL", "en_GB.UTF-8", 1) == 0);
    assert(ft5955_EnumSystemLocalesW(callback, FT5955_LCID_INSTALLED));
    assert(count == 1 && seen_gb == 1);
    reset();
    assert(setenv("LC_ALL", "en_US.UTF-8", 1) == 0);
    assert(ft5955_EnumSystemLocalesW(callback, FT5955_LCID_INSTALLED));
    assert(count == 1 && seen_us == 1);
    reset();
    assert(!ft5955_EnumSystemLocalesW(NULL, FT5955_LCID_SUPPORTED));
    assert(!ft5955_EnumSystemLocalesW(callback, 3));
    assert(!ft5955_EnumSystemLocalesW(callback, 4));
    assert(count == 0);
    puts("5955 restricted locale enumeration: synthetic tests OK");
    return 0;
}
