/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Read-only, synthetic tests of supported MOH locale information.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_locale.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static void expect(uint32_t lcid, uint32_t type, const char *wanted)
{
    uint16_t buffer[128];
    size_t len = strlen(wanted) + 1;
    for (size_t i = 0; i < 128; ++i)
        buffer[i] = 0x1234;
    assert(ft5955_GetLocaleInfoW(lcid, type, NULL, 0) == (int)len);
    assert(ft5955_GetLocaleInfoW(lcid, type, buffer, (int)len - 1) == 0);
    assert(buffer[0] == 0x1234); /* insufficient buffer does not write */
    assert(ft5955_GetLocaleInfoW(lcid, type, buffer, (int)len) == (int)len);
    for (size_t i = 0; i < len; ++i)
        assert(buffer[i] == (unsigned char)wanted[i]);
}

int main(void)
{
    expect(FT5955_LCID_EN_GB, FT5955_LTYPE_SSHORTDATE, "dd/MM/yyyy");
    expect(FT5955_LCID_EN_US, FT5955_LTYPE_SSHORTDATE, "M/d/yyyy");
    expect(FT5955_LCID_INVARIANT, FT5955_LTYPE_SSHORTDATE, "yyyy-MM-dd");
    expect(FT5955_LCID_EN_GB, FT5955_LTYPE_STIMEFORMAT, "HH:mm:ss");
    expect(FT5955_LCID_EN_US, FT5955_LTYPE_STIMEFORMAT, "h:mm:ss tt");
    expect(FT5955_LCID_EN_GB, FT5955_LTYPE_SNAME, "en-GB");
    expect(FT5955_LCID_EN_US, FT5955_LTYPE_SNAME, "en-US");
    expect(FT5955_LCID_EN_GB, FT5955_LTYPE_SDECIMAL, ".");
    expect(FT5955_LCID_EN_GB, FT5955_LTYPE_S1159, "AM");
    uint16_t out[128] = {0xaaaa};
    assert(!ft5955_GetLocaleInfoW(FT5955_LCID_EN_GB, 0xffffffffu, out, 128));
    assert(!ft5955_GetLocaleInfoW(0x040c, FT5955_LTYPE_SSHORTDATE, out, 128));
    assert(!ft5955_GetLocaleInfoW(FT5955_LCID_EN_GB, FT5955_LTYPE_SSHORTDATE, out, -1));
    assert(!ft5955_GetLocaleInfoW(FT5955_LCID_EN_GB, FT5955_LTYPE_SSHORTDATE, NULL, 32));
    assert(out[0] == 0xaaaa);
    puts("5955 locale-info shims: synthetic tests OK");
    return 0;
}
