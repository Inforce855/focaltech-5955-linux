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

/* Only conservative, known English/invariant strings are exported.
 * WIN32 LOCALE_RETURN_NUMBER, LOCALE_NOUSEROVERRIDE, and other modifiers
 * are unsupported, and return 0. No output is written on failure. */
int FT5955_LOCALE_MS
ft5955_GetLocaleInfoW(uint32_t lcid, uint32_t type, uint16_t *output, int capacity)
{
    if (capacity < 0)
        return 0;
    if (lcid == FT5955_LCID_USER_DEFAULT ||
        lcid == FT5955_LCID_SYSTEM_DEFAULT)
        lcid = preferred_locale();
    const int gb = (lcid == FT5955_LCID_EN_GB);
    const int us = (lcid == FT5955_LCID_EN_US);
    const int invariant = (lcid == FT5955_LCID_INVARIANT);
    if (!gb && !us && !invariant)
        return 0;
    const char *value = NULL;
    switch (type) {
    case FT5955_LTYPE_SLIST: value = ","; break;
    case FT5955_LTYPE_SDECIMAL: value = "."; break;
    case FT5955_LTYPE_STHOUSAND: value = ","; break;
    case FT5955_LTYPE_SDATE: value = invariant ? "-" : "/"; break;
    case FT5955_LTYPE_STIME: value = ":"; break;
    case FT5955_LTYPE_SSHORTDATE:
        value = gb ? "dd/MM/yyyy" : us ? "M/d/yyyy" : "yyyy-MM-dd";
        break;
    case FT5955_LTYPE_SLONGDATE:
        value = gb ? "dddd, d MMMM yyyy" : us ? "dddd, MMMM d, yyyy" :
                     "dddd, dd MMMM yyyy";
        break;
    case FT5955_LTYPE_S1159: value = "AM"; break;
    case FT5955_LTYPE_S2359: value = "PM"; break;
    case FT5955_LTYPE_SNAME:
        value = gb ? "en-GB" : us ? "en-US" : "";
        break;
    case FT5955_LTYPE_STIMEFORMAT:
        value = us ? "h:mm:ss tt" : "HH:mm:ss";
        break;
    default:
        return 0;
    }
    size_t size = strlen(value) + 1;
    if (size > 128)
        return 0;
    if (capacity == 0)
        return (int)size;
    if (!output || (size_t)capacity < size)
        return 0;
    for (size_t i = 0; i < size; ++i)
        output[i] = (unsigned char)value[i];
    return (int)size;
}
