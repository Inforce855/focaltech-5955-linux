/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Private binary metadata check. Never maps executable pages or calls DLL.
 * Invoked on a SHA-verified temp extraction by moh_pe_guard_probe.py.
 */
#include "ft5955_pe_guard.h"
#include <stdio.h>
#include <stdlib.h>

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
    free(bytes);
    if (result != 0) {
        puts("5955 PE guard: REJECTED — header or section layout unsupported.");
        puts("The loader remains blocked. Do not enable PE execution.");
        return 1;
    }
    puts("5955 PE guard: verified MOH image headers accepted (offline).");
    printf("  Preferred base: 0x%llx\n", (unsigned long long)layout.image_base);
    printf("  Image size: %u bytes\n", layout.image_size);
    printf("  Section count: %u\n", (unsigned)layout.section_count);
    printf("  Import directory RVA: 0x%x\n", layout.import_rva);
    puts("No Windows DLL code executed; no USB, biometrics or authentication accessed.");
    return 0;
}
