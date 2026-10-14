/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Offline Windows x64 SYSTEM_INFO ABI and overwrite-canary tests.
 * No Windows DLL, USB, fingerprint image or system authentication.
 */
#include "ft5955_compat_sysinfo.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static unsigned failures;
#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr,"5955 SYSTEM_INFO test line %d: %s\n",__LINE__,#expr); \
    failures++; \
} } while (0)

int main(void)
{
    struct {
        uint8_t before[16];
        ft5955_system_info info;
        uint8_t after[16];
    } guarded;
    memset(&guarded, 0xa5, sizeof guarded);
    ft5955_GetSystemInfo(&guarded.info);
    CHECK(sizeof guarded.info == 48);
    for (size_t i=0;i<sizeof guarded.before;i++)
        CHECK(guarded.before[i] == 0xa5);
    for (size_t i=0;i<sizeof guarded.after;i++)
        CHECK(guarded.after[i] == 0xa5);
    CHECK(guarded.info.processor_architecture == 9);
    CHECK(guarded.info.reserved == 0);
    CHECK(guarded.info.processor_type == 8664);
    CHECK(guarded.info.allocation_granularity == 65536u);
    CHECK((uintptr_t)guarded.info.minimum_application_address == 0x10000u);
    CHECK((uintptr_t)guarded.info.maximum_application_address ==
          UINT64_C(0x00007fffffffffff));
    long pagesize=sysconf(_SC_PAGESIZE);
    if (pagesize > 0 && (uint64_t)pagesize <= UINT32_MAX)
        CHECK(guarded.info.page_size == (uint32_t)pagesize);
    long online=sysconf(_SC_NPROCESSORS_ONLN);
    if (online > 0) {
        uint32_t n=online>64 ? 64u : (uint32_t)online;
        CHECK(guarded.info.number_of_processors == n);
        uint64_t expected_mask=n==64 ? UINT64_MAX : (UINT64_C(1)<<n)-1u;
        CHECK(guarded.info.active_processor_mask == expected_mask);
    }
    /* Repeated calls must not damage adjacent caller-owned data. */
    ft5955_GetSystemInfo(&guarded.info);
    CHECK(guarded.before[0] == 0xa5 && guarded.after[15] == 0xa5);
    ft5955_GetSystemInfo(NULL);
    if (failures) {
        fprintf(stderr,"5955 SYSTEM_INFO: %u synthetic failures\n",failures);
        return 1;
    }
    puts("5955 Win64 SYSTEM_INFO exact layout and buffer canaries: synthetic tests OK");
    return 0;
}
