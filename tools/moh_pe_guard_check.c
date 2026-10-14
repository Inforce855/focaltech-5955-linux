/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Private binary metadata check. Never maps executable pages or calls DLL.
 * Invoked on a SHA-verified temp extraction by moh_pe_guard_probe.py.
 */
#include "ft5955_pe_guard.h"
#include "ft5955_pe_exports.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: moh_pe_guard_check <private DLL path>\n");
        return 2;
    }
    FILE *file = fopen(argv[1], "rb");
    if (!file) {
        perror("open PE for offline inspection");
        return 2;
    }
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return 2;
    }
    long length = ftell(file);
    if (length < 0x100 || (unsigned long)length > FT5955_PE_FILE_LIMIT ||
        fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return 2;
    }
    unsigned char *bytes = malloc((size_t)length);
    if (!bytes) {
        fclose(file);
        return 2;
    }
    size_t read_count = fread(bytes, 1, (size_t)length, file);
    fclose(file);
    if (read_count != (size_t)length) {
        free(bytes);
        return 2;
    }
    struct ft5955_pe_layout layout;
    int result = ft5955_pe_guard(bytes, (size_t)length, &layout);
    if (result != 0) {
        puts("5955 PE guard: REJECTED — header or section layout unsupported.");
        puts("The loader remains blocked. Do not enable PE execution.");
        free(bytes);
        return 1;
    }
    /* Reconstruct a non-executable image in malloc'd memory.
     * This is data copying only: no mmap(PROT_EXEC), GS or DLL calls. */
    unsigned char *img = calloc(1, layout.image_size);
    if (!img) {
        free(bytes);
        return 2;
    }
    memcpy(img,bytes,layout.headers_size);
    int executable = 0;
    for (unsigned i=0;i<layout.section_count;i++) {
        size_t at=(size_t)layout.section_table+i*40u;
        uint32_t rva, raw_size, raw_offset;
        memcpy(&rva,bytes+at+12,4);
        memcpy(&raw_size,bytes+at+16,4);
        memcpy(&raw_offset,bytes+at+20,4);
        if (raw_size) memcpy(img+rva,bytes+raw_offset,raw_size);
    }
    uint32_t export_rva, export_size, function_rva = 0;
    size_t dir=(size_t)layout.nt_offset+24u+112u;
    memcpy(&export_rva,bytes+dir,4);
    memcpy(&export_size,bytes+dir+4,4);
    result=ft5955_pe_find_export(img,layout.image_size,export_rva,
                                 export_size,"WbioQueryEngineInterface",
                                 &function_rva);
    if (result==0) {
        for (unsigned i=0;i<layout.section_count;i++) {
            size_t at=(size_t)layout.section_table+i*40u;
            uint32_t va,vsize,raw,flags;
            memcpy(&va,bytes+at+12,4);
            memcpy(&vsize,bytes+at+8,4);
            memcpy(&raw,bytes+at+16,4);
            memcpy(&flags,bytes+at+36,4);
            uint32_t span=vsize>raw?vsize:raw;
            if (function_rva>=va && (uint64_t)function_rva-va<span &&
                (flags & 0x20000000u)) executable=1;
        }
    }
    free(img);
    free(bytes);
    if (result!=0 || !executable) {
        puts("5955 PE export preflight: WbioQueryEngineInterface is absent, malformed or not executable.");
        puts("DLL was not executed. Loader remains locked.");
        return 1;
    }
    puts("5955 PE guard: verified MOH image headers accepted (offline).");
    puts("5955 PE export preflight: WbioQueryEngineInterface RVA validated (offline).");
    printf("  Preferred base: 0x%llx\n", (unsigned long long)layout.image_base);
    printf("  Image size: %u bytes\n", layout.image_size);
    printf("  Section count: %u\n", (unsigned)layout.section_count);
    printf("  Import directory RVA: 0x%x\n", layout.import_rva);
    puts("No Windows DLL code executed; no USB, biometrics or authentication accessed.");
    return 0;
}
