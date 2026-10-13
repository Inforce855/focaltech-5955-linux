/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Offline PE32+ header/section bounds guard for the experimental 5955 loader.
 * Checks ONLY structures needed before the inherited loader copies sections;
 * it does not validate the full import/export/resource graph.
 */
#ifndef FT5955_PE_GUARD_H
#define FT5955_PE_GUARD_H
#include <stddef.h>
#include <stdint.h>
#define FT5955_PE_FILE_LIMIT (32u * 1024u * 1024u)
#define FT5955_PE_IMAGE_LIMIT (64u * 1024u * 1024u)
struct ft5955_pe_layout {
    uint32_t nt_offset;
    uint32_t image_size;
    uint32_t headers_size;
    uint32_t entry_rva;
    uint32_t import_rva;
    uint32_t import_size;
    uint16_t section_count;
    uint64_t section_table;
    uint64_t image_base;
};
/* 0 for structurally bounded/supported; -1 for rejected headers.
 * Rejects any PE TLS directory. Caller still must audit IAT/export bounds.
 */
int ft5955_pe_guard(const uint8_t *bytes, size_t length,
                    struct ft5955_pe_layout *layout);
#endif
