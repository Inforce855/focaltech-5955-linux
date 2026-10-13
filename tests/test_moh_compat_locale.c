/* SPDX-License-Identifier: LGPL-2.1-or-later */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_locale.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    assert(setenv("LC_ALL", "en_GB.UTF-8", 1) == 0);
    assert(ft5955_GetUserDefaultLCID() == FT5955_LCID_EN_GB);
    assert(ft5955_IsValidLocale(FT5955_LCID_EN_GB, FT5955_LCID_INSTALLED));
    assert(ft5955_IsValidLocale(FT5955_LCID_EN_US, FT5955_LCID_SUPPORTED));
    assert(ft5955_IsValidLocale(FT5955_LCID_USER_DEFAULT, FT5955_LCID_INSTALLED));
    assert(!ft5955_IsValidLocale(0x040c, FT5955_LCID_SUPPORTED));
    assert(!ft5955_IsValidLocale(FT5955_LCID_EN_GB, 0xffffffffu));
    assert(!ft5955_IsValidLocale(FT5955_LCID_EN_GB, 0));
    assert(setenv("LC_ALL", "en_US.UTF-8", 1) == 0);
    assert(ft5955_GetUserDefaultLCID() == FT5955_LCID_EN_US);
    assert(setenv("LC_ALL", "fr_FR.UTF-8", 1) == 0);
    assert(ft5955_GetUserDefaultLCID() == FT5955_LCID_INVARIANT);
    assert(ft5955_IsValidLocale(FT5955_LCID_INVARIANT, FT5955_LCID_SUPPORTED));
    puts("5955 restricted locale shims: synthetic tests OK");
    return 0;
}
