/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Strictly synthetic GetTempPathW semantics: no disk access.
 */
#include "ft5955_compat_temp.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main(void)
{
    static const uint16_t expected[] = {
        'C',':','\\','W','i','n','d','o','w','s','\\',
        'T','e','m','p','\\',0
    };
    const uint32_t required = (uint32_t)(sizeof expected / sizeof expected[0]);
    uint16_t buffer[64];
    for (unsigned i = 0; i < 64; ++i)
        buffer[i] = 0x5a5au;
    assert(ft5955_GetTempPathW(0, NULL) == required);
    assert(ft5955_GetTempPathW(64, NULL) == required);
    assert(ft5955_GetTempPathW(required - 1, buffer) == required);
    assert(buffer[0] == 0x5a5au);
    assert(ft5955_GetTempPathW(required, buffer) == required - 1);
    for (uint32_t i = 0; i < required; ++i)
        assert(buffer[i] == expected[i]);
    assert(buffer[required] == 0x5a5au);
    puts("5955 virtual temp path shim: synthetic tests OK");
    return 0;
}
