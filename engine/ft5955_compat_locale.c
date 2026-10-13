/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Narrow locale API for known English LCIDs. No globally mutable setlocale.
 * This is intentionally not a general Windows NLS emulation.
 */
#include "ft5955_compat_locale.h"
#include <stdlib.h>
#include <string.h>

static uint32_t preferred_locale(void)
{
    const char *p = getenv("LC_ALL");
    if (!p || !*p) p = getenv("LC_MESSAGES");
    if (!p || !*p) p = getenv("LANG");
    if (p && strncmp(p, "en_GB", 5) == 0)
        return FT5955_LCID_EN_GB;
    if (p && strncmp(p, "en_US", 5) == 0)
        return FT5955_LCID_EN_US;
    /* Unknown Linux locales cannot be represented in this restricted
     * implementation: use Win32 invariant rather than claim en-US. */
    return FT5955_LCID_INVARIANT;
}

uint32_t FT5955_LOCALE_MS ft5955_GetUserDefaultLCID(void)
{
    return preferred_locale();
}

int FT5955_LOCALE_MS
ft5955_IsValidLocale(uint32_t lcid, uint32_t flags)
{
    if (flags != FT5955_LCID_INSTALLED && flags != FT5955_LCID_SUPPORTED)
        return 0;
    if (lcid == FT5955_LCID_USER_DEFAULT ||
        lcid == FT5955_LCID_SYSTEM_DEFAULT)
        lcid = preferred_locale();
    return lcid == FT5955_LCID_EN_US || lcid == FT5955_LCID_EN_GB ||
           lcid == FT5955_LCID_INVARIANT;
}
