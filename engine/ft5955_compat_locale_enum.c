/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Minimal Win32 EnumSystemLocalesW adapter for the MOH engine experiment.
 *
 * Deliberately enumerates ONLY the same English LCIDs supported by
 * ft5955_GetLocaleInfoW. Does not claim to emulate all installed Windows
 * locales. Callback invocation uses the Windows x64 calling convention.
 */
#include "ft5955_compat_locale.h"

int FT5955_LOCALE_MS
ft5955_EnumSystemLocalesW(ft5955_locale_enum_callback callback, uint32_t flags)
{
    /* Provide private mutable buffers to this invocation's callback. */
    uint16_t id_en_us[] = {'0','0','0','0','0','4','0','9',0};
    uint16_t id_en_gb[] = {'0','0','0','0','0','8','0','9',0};
    if (!callback)
        return 0;
    /* Windows: flags=0 means LCID_SUPPORTED. Alternate sorts and mixed
     * LCID_SUPPORTED/LCID_INSTALLED flags are intentionally unsupported. */
    if (flags != 0 && flags != FT5955_LCID_SUPPORTED &&
        flags != FT5955_LCID_INSTALLED)
        return 0;
    if (flags == FT5955_LCID_INSTALLED) {
        uint32_t current = ft5955_GetUserDefaultLCID();
        if (current == FT5955_LCID_EN_GB)
            (void)callback(id_en_gb);
        else if (current == FT5955_LCID_EN_US)
            (void)callback(id_en_us);
        return 1;
    }
    /* On Windows, the callback may stop enumeration by returning FALSE. */
    if (!callback(id_en_us))
        return 1;
    (void)callback(id_en_gb);
    return 1;
}
