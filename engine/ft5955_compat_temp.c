/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Narrow GetTempPathW for a virtual, closed Windows namespace.
 * The returned string is not a Linux host path and does not authorise writes.
 * CreateFileW remains disabled in this engine-bridge prototype.
 */
#include "ft5955_compat_temp.h"
#include <stddef.h>

uint32_t FT5955_TEMP_MS
ft5955_GetTempPathW(uint32_t length, uint16_t *buffer)
{
    static const uint16_t path[] = {
        'C',':','\\','W','i','n','d','o','w','s','\\',
        'T','e','m','p','\\',0
    };
    const uint32_t required = (uint32_t)(sizeof(path) / sizeof(path[0]));
    if (!buffer || length < required)
        return required;
    for (uint32_t i = 0; i < required; ++i)
        buffer[i] = path[i];
    return required - 1;
}
