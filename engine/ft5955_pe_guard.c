/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Reject malformed/truncated PE inputs before the inherited loader performs
 * unbounded f32()/memcpy() operations. Not a substitute for full PE parsing.
 */
#include "ft5955_pe_guard.h"
#include <stdint.h>
#include <string.h>

#define MAX_SECTIONS 96u

static int within(size_t size, size_t at, size_t count)
{
    return at <= size && count <= size - at;
}
static uint16_t rd16(const uint8_t *p)
{
    uint16_t v;
    memcpy(&v, p, sizeof v);
    return v;
}
static uint32_t rd32(const uint8_t *p)
{
    uint32_t v;
    memcpy(&v, p, sizeof v);
    return v;
}
static uint64_t rd64(const uint8_t *p)
{
    uint64_t v;
    memcpy(&v, p, sizeof v);
    return v;
}
static int image_range(uint32_t image_size, uint32_t rva, uint32_t len)
{
    return rva <= image_size && len <= image_size - rva;
}
int ft5955_pe_guard(const uint8_t *file, size_t filelen,
                    struct ft5955_pe_layout *out)
{
    if (!file || !out || filelen < 0x100 ||
        filelen > FT5955_PE_FILE_LIMIT ||
        rd16(file) != 0x5a4d)
        return -1;
    const uint32_t nt = rd32(file + 0x3c);
    if (!within(filelen, nt, 24) || rd32(file + nt) != 0x00004550)
        return -1;
    if (rd16(file + nt + 4) != 0x8664)
        return -1; /* x64 AMD64 only */
    const uint16_t count = rd16(file + nt + 6);
    const uint16_t optsize = rd16(file + nt + 20);
    const size_t opt = (size_t)nt + 24;
    if (count == 0 || count > MAX_SECTIONS || optsize < 240 ||
        !within(filelen, opt, optsize) ||
        rd16(file + opt) != 0x20b)
        return -1;
    const uint32_t image_size = rd32(file + opt + 56);
    const uint32_t headers = rd32(file + opt + 60);
    const uint32_t entry = rd32(file + opt + 16);
    const uint64_t imagebase = rd64(file + opt + 24);
    if (!image_size || image_size > FT5955_PE_IMAGE_LIMIT ||
        !headers || headers > filelen || headers > image_size ||
        (headers & 0xfffu) || (image_size & 0xfffu) ||
        !image_range(image_size, entry, 1) ||
        imagebase < 0x10000u)
        return -1;
    if (rd32(file + opt + 108) < 10)
        return -1; /* TLS and import data-directory slots must exist */
    const uint32_t import = rd32(file + opt + 112 + 8);
    const uint32_t importsize = rd32(file + opt + 112 + 8 + 4);
    const uint32_t tls = rd32(file + opt + 112 + 9 * 8);
    const uint32_t tlssize = rd32(file + opt + 112 + 9 * 8 + 4);
    if (tls || tlssize ||
        !import || importsize < 20 ||
        !image_range(image_size, import, importsize))
        return -1;
    const size_t sect = opt + optsize;
    if (!within(filelen, sect, (size_t)count * 40) ||
        sect + (size_t)count * 40 > headers)
        return -1;

    uint32_t starts[MAX_SECTIONS], ends[MAX_SECTIONS];
    int entry_exec = 0, import_file_backed = 0;
    for (unsigned i = 0; i < count; ++i) {
        const size_t at = sect + (size_t)i * 40;
        const uint32_t virt_size = rd32(file + at + 8);
        const uint32_t vaddr = rd32(file + at + 12);
        const uint32_t raw_size = rd32(file + at + 16);
        const uint32_t raw_ptr = rd32(file + at + 20);
        const uint32_t chars = rd32(file + at + 36);
        const uint32_t span = virt_size > raw_size ? virt_size : raw_size;
        if ((vaddr & 0xfffu) || vaddr < headers ||
            !image_range(image_size, vaddr, span) ||
            (raw_size && !within(filelen, raw_ptr, raw_size)) ||
            ((chars & 0x20000000u) && (chars & 0x80000000u)))
            return -1;
        if (span > UINT32_MAX - 0xfffu)
            return -1;
        const uint32_t end = vaddr + ((span + 0xfffu) & ~0xfffu);
        if (end > image_size)
            return -1;
        for (unsigned j = 0; j < i; ++j) {
            if (span && starts[j] != ends[j] &&
                vaddr < ends[j] && starts[j] < end)
                return -1;
        }
        starts[i] = vaddr;
        ends[i] = span ? end : vaddr;
        if (entry >= vaddr && entry - vaddr < span &&
            (chars & 0x20000000u))
            entry_exec = 1;
        if (import >= vaddr && import - vaddr < raw_size &&
            importsize <= raw_size - (import - vaddr))
            import_file_backed = 1;
    }
    if (!entry_exec || !import_file_backed)
        return -1;
    *out = (struct ft5955_pe_layout){
        .nt_offset = nt,
        .image_size = image_size,
        .headers_size = headers,
        .entry_rva = entry,
        .import_rva = import,
        .import_size = importsize,
        .section_count = count,
        .section_table = sect,
        .image_base = imagebase,
    };
    return 0;
}
