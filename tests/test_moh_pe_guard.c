/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic minimal PE32+ fixture; no proprietary DLL, USB or biometrics.
 */
#include "ft5955_pe_guard.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define LEN 0xc00u
#define NT 0x80u
#define OPT (NT+24u)
#define S1 (OPT+240u)
#define S2 (S1+40u)
static void wr16(uint8_t *p, size_t at, uint16_t value)
{ memcpy(p+at, &value, sizeof value); }
static void wr32(uint8_t *p, size_t at, uint32_t value)
{ memcpy(p+at, &value, sizeof value); }
static void wr64(uint8_t *p, size_t at, uint64_t value)
{ memcpy(p+at, &value, sizeof value); }

static void fixture(uint8_t *file)
{
    memset(file, 0, LEN);
    wr16(file, 0, 0x5a4d);
    wr32(file, 0x3c, NT);
    wr32(file, NT, 0x00004550);
    wr16(file, NT+4, 0x8664);
    wr16(file, NT+6, 2);
    wr16(file, NT+20, 240);
    wr16(file, OPT, 0x20b);
    wr32(file, OPT+16, 0x1000); /* code entry */
    wr64(file, OPT+24, UINT64_C(0x180000000));
    wr32(file, OPT+56, 0x4000); /* mapped image */
    wr32(file, OPT+60, 0x400); /* on-disk header alignment */
    wr32(file, OPT+108, 16); /* number of data directories */
    wr32(file, OPT+112+8, 0x2100); /* import directory */
    wr32(file, OPT+112+8+4, 0x40); /* size */
    wr32(file, S1+8, 0x400); /* code virtual size */
    wr32(file, S1+12, 0x1000);
    wr32(file, S1+16, 0x400);
    wr32(file, S1+20, 0x400);
    wr32(file, S1+36, 0x60000020);
    wr32(file, S2+8, 0x400); /* data virtual size */
    wr32(file, S2+12, 0x2000);
    wr32(file, S2+16, 0x400);
    wr32(file, S2+20, 0x800);
    wr32(file, S2+36, 0xc0000040);
}
/* Report failed cases with a source line rather than aborting with SIGABRT
 * and leaving a core dump in the user's systemd-coredump directory. */
static unsigned failures;
#define CHECK(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "PE guard test failed on line %d: %s\\n", __LINE__, #expr); \
        ++failures; \
    } \
} while (0)

static void rejected_line(const uint8_t *p, size_t len, int case_line)
{
    struct ft5955_pe_layout d;
    memset(&d, 0xa5, sizeof d);
    int result = ft5955_pe_guard(p, len, &d);
    if (result != -1) {
        fprintf(stderr, "PE guard unexpectedly accepted malformed input from line %d (result=%d)\\n",
                case_line, result);
        ++failures;
    }
}
#define rejected(p, len) rejected_line((p), (len), __LINE__)
int main(void)
{
    uint8_t p[LEN];
    struct ft5955_pe_layout d;
    fixture(p);
    CHECK(ft5955_pe_guard(p, LEN, &d) == 0);
    CHECK(d.image_size == 0x4000 && d.headers_size == 0x400);
    CHECK(d.entry_rva == 0x1000 && d.section_count == 2);
    CHECK(d.import_rva == 0x2100 && d.import_size == 0x40);
    CHECK(d.image_base == UINT64_C(0x180000000));
    CHECK(d.section_table == S1);
    rejected(p, 0x200); /* truncated before section raw data */
    rejected(p, 0);     /* empty file */

    fixture(p); wr16(p, 0, 0); rejected(p, LEN);
    fixture(p); wr32(p, 0x3c, UINT32_MAX); rejected(p, LEN);
    fixture(p); wr32(p, NT, 0); rejected(p, LEN);
    fixture(p); wr16(p, NT+4, 0x014c); rejected(p, LEN);
    fixture(p); wr16(p, NT+6, 97); rejected(p, LEN);
    fixture(p); wr16(p, NT+20, 120); rejected(p, LEN);
    fixture(p); wr16(p, OPT, 0x10b); rejected(p, LEN);
    fixture(p); wr32(p, OPT+56, 0x2000); rejected(p, LEN);
    fixture(p); wr32(p, OPT+60, 0x4001); rejected(p, LEN);
    fixture(p); wr32(p, OPT+16, 0x2100); rejected(p, LEN);
    fixture(p); wr32(p, OPT+112+8, 0); rejected(p, LEN);
    fixture(p); wr32(p, OPT+112+8, 0x3900); rejected(p, LEN);
    /* The import data starts 0x100 into a 0x400-byte raw section:
     * exactly 0x300 bytes FIT and must be accepted. One extra byte fails. */
    fixture(p); wr32(p, OPT+112+8+4, 0x300);
    CHECK(ft5955_pe_guard(p, LEN, &d) == 0);
    fixture(p); wr32(p, OPT+112+8+4, 0x301); rejected(p, LEN);
    fixture(p); wr32(p, OPT+112+9*8, 0x2800); rejected(p, LEN);
    fixture(p); wr32(p, OPT+112+9*8+4, 1); rejected(p, LEN);
    fixture(p); wr32(p, S1+20, 0xb00); rejected(p, LEN); /* raw file overflow */
    fixture(p); wr32(p, S1+12, 0x2000); rejected(p, LEN); /* sections overlap */
    fixture(p); wr32(p, S1+12, 0x400); rejected(p, LEN); /* unaligned virtual address */
    fixture(p); wr32(p, S1+36, 0xe0000020); rejected(p, LEN); /* W+X */
    fixture(p); wr32(p, S1+8, UINT32_MAX); rejected(p, LEN);
    fixture(p); wr32(p, S2+16, 0x100); rejected(p, LEN); /* import not raw-backed */
    if (failures) {
        fprintf(stderr, "5955 PE guard: %u synthetic case(s) failed\\n", failures);
        return 1;
    }
    puts("5955 conservative PE header/section guard: synthetic tests OK");
    return 0;
}
