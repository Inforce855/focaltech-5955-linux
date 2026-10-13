/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Bounded IMAGE_EXPORT_DIRECTORY interpreter, no vendor PE execution.
 * Rejects corrupt tables, ordinals, missing terminators and forwarded exports.
 */
#include "ft5955_pe_exports.h"
#include <stdint.h>
#include <string.h>

static int inside(size_t size, uint64_t at, uint64_t n)
{
    return at <= size && n <= size-at;
}
static uint16_t read16(const uint8_t *p)
{
    uint16_t v;
    memcpy(&v,p,sizeof v);
    return v;
}
static uint32_t read32(const uint8_t *p)
{
    uint32_t v;
    memcpy(&v,p,sizeof v);
    return v;
}
int ft5955_pe_find_export(const uint8_t *img, size_t size,
                          uint32_t dir, uint32_t dirlen,
                          const char *requested, uint32_t *out)
{
    if (!img || !requested || !out || !requested[0] ||
        !inside(size,dir,dirlen) || dirlen < 40u || !dir)
        return -1;
    /* Avoid reading arbitrary caller strings: all requests originate
     * from the loader's fixed, short export name. */
    const char *end = memchr(requested,0,256);
    if (!end) return -1;
    const size_t wantlen = (size_t)(end-requested);
    const uint8_t *d = img+dir;
    const uint32_t nfunc = read32(d+20);
    const uint32_t nnames = read32(d+24);
    const uint32_t func_table = read32(d+28);
    const uint32_t names = read32(d+32);
    const uint32_t ordinals = read32(d+36);
    if (!nfunc || !nnames || nnames > nfunc ||
        !inside(size,func_table,(uint64_t)nfunc*4u) ||
        !inside(size,names,(uint64_t)nnames*4u) ||
        !inside(size,ordinals,(uint64_t)nnames*2u))
        return -1;
    for (uint32_t i=0;i<nnames;i++) {
        uint32_t name_rva = read32(img+names+(size_t)i*4u);
        if (!inside(size,name_rva,1)) return -1;
        const uint8_t *start=img+name_rva;
        const uint8_t *stop=memchr(start,0,size-name_rva);
        if (!stop) return -1;
        if ((size_t)(stop-start)!=wantlen ||
            memcmp(start,requested,wantlen)!=0)
            continue;
        uint16_t idx=read16(img+ordinals+(size_t)i*2u);
        if (idx >= nfunc) return -1;
        uint32_t rva=read32(img+func_table+(size_t)idx*4u);
        if (!rva || !inside(size,rva,1)) return -1;
        /* A function RVA within the export directory is a forwarder
         * string, not callable code. Never treat it as a function. */
        if ((uint64_t)rva >= dir && (uint64_t)rva < (uint64_t)dir+dirlen)
            return -1;
        *out=rva;
        return 0;
    }
    return -1;
}
