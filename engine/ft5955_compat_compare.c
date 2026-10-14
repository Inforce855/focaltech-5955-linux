/* SPDX-License-Identifier: LGPL-2.1-or-later
 * NARROW, EXPERIMENTAL CompareStringW. This is not a full Windows NLS
 * collator and MUST NOT be used to make security decisions.
 *
 * Only ASCII U+0020..U+007E and en-GB/en-US/invariant locale IDs are
 * accepted. Only flags 0 and NORM_IGNORECASE are supported.
 * Unsupported data returns 0 (Win32 comparison error), never a guessed
 * equivalence. Before executing the actual MOH engine, determine which
 * comparison flags and string classes it uses.
 */
#include "ft5955_compat_compare.h"
#include "ft5955_compat_locale.h"
#include <stddef.h>

#define FT5955_COMPARE_LIMIT 4096

static int permitted_locale(uint32_t lcid)
{
    if (lcid == 0 || lcid == FT5955_LCID_USER_DEFAULT ||
        lcid == FT5955_LCID_SYSTEM_DEFAULT)
        lcid = ft5955_GetUserDefaultLCID();
    return lcid == FT5955_LCID_EN_GB || lcid == FT5955_LCID_EN_US ||
           lcid == FT5955_LCID_INVARIANT;
}

static int get_length(const uint16_t *data, int supplied, int *result)
{
    if (!data || supplied == 0 || supplied < -1 || supplied > FT5955_COMPARE_LIMIT)
        return 0;
    if (supplied >= 0) {
        *result = supplied;
        return 1;
    }
    for (int i = 0; i < FT5955_COMPARE_LIMIT; ++i) {
        if (data[i] == 0) {
            *result = i;
            return 1;
        }
    }
    return 0;
}

static uint16_t lowercase_ascii(uint16_t c)
{
    return c >= 'A' && c <= 'Z' ? (uint16_t)(c + ('a' - 'A')) : c;
}

int FT5955_COMPARE_MS ft5955_CompareStringW(uint32_t lcid, uint32_t flags,
    const uint16_t *a, int supplied_a, const uint16_t *b, int supplied_b)
{
    int na = 0, nb = 0;
    if (!permitted_locale(lcid) ||
        (flags != 0 && flags != FT5955_NORM_IGNORECASE) ||
        !get_length(a, supplied_a, &na) ||
        !get_length(b, supplied_b, &nb))
        return 0;

    /* Validate complete inputs before comparing so a less/greater result
     * cannot conceal unsupported UTF-16 elsewhere in the string. */
    for (int i = 0; i < na; ++i)
        if (a[i] < 0x20 || a[i] > 0x7e) return 0;
    for (int i = 0; i < nb; ++i)
        if (b[i] < 0x20 || b[i] > 0x7e) return 0;

    /* ASCII approximate lexical order, NOT Windows collation equivalence.
     * The full DLL import may rely on linguistic sorting and must be traced.
     */
    int count = na < nb ? na : nb;
    for (int i = 0; i < count; ++i) {
        uint16_t ca = a[i], cb = b[i];
        if (flags & FT5955_NORM_IGNORECASE) {
            ca = lowercase_ascii(ca);
            cb = lowercase_ascii(cb);
        }
        if (ca < cb) return FT5955_CSTR_LESS_THAN;
        if (ca > cb) return FT5955_CSTR_GREATER_THAN;
    }
    if (na < nb) return FT5955_CSTR_LESS_THAN;
    if (na > nb) return FT5955_CSTR_GREATER_THAN;
    return FT5955_CSTR_EQUAL;
}
