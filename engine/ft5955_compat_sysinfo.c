/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Windows SYSTEM_INFO compatibility. The FT9201 loader previously wrote
 * 64 bytes into a 48-byte x64 structure (eight-byte fields at offsets
 * 8, 16 and 24), risking an overwrite of the caller's stack.
 *
 * CPU mask is a VIRTUAL Windows processor group of up to 64 logical CPUs,
 * not an actual Windows processor affinity mask. VirtualAlloc allocation
 * granularity is fixed at 64 KiB even if Linux page size is smaller.
 * Neither VirtualAlloc nor Windows processor groups are implemented.
 */
#include "ft5955_compat_sysinfo.h"
#include <cpuid.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

void FT5955_SYSINFO_MS ft5955_GetSystemInfo(ft5955_system_info *out)
{
    if (!out) return; /* Win32 expects non-NULL; fail harmlessly offline. */
    ft5955_system_info info;
    memset(&info, 0, sizeof info);
    info.processor_architecture = 9; /* PROCESSOR_ARCHITECTURE_AMD64 */
    info.processor_type = 8664;       /* PROCESSOR_AMD_X8664 */
    info.allocation_granularity = 65536u;
    /* Synthetic x64 user-mode address range, not a Linux mmap promise. */
    info.minimum_application_address = (void *)(uintptr_t)0x10000u;
    info.maximum_application_address = (void *)(uintptr_t)UINT64_C(0x00007fffffffffff);
    long pagesize = sysconf(_SC_PAGESIZE);
    if (pagesize > 0 && (uint64_t)pagesize <= UINT32_MAX)
        info.page_size = (uint32_t)pagesize;
    long processors = sysconf(_SC_NPROCESSORS_ONLN);
    if (processors > 0) {
        uint32_t count = processors > 64 ? 64u : (uint32_t)processors;
        info.number_of_processors = count;
        info.active_processor_mask = count == 64 ? UINT64_MAX :
                                     (UINT64_C(1) << count)-1u;
    }
    /* CPUID leaf 1 reports family/model/stepping used by Windows' legacy
     * display-only processor level and revision fields. */
    unsigned eax=0, ebx=0, ecx=0, edx=0;
    if (__get_cpuid(1u, &eax, &ebx, &ecx, &edx)) {
        uint32_t family = (eax >> 8) & 15u;
        uint32_t model = (eax >> 4) & 15u;
        uint32_t stepping = eax & 15u;
        if (family == 15u) family += (eax >> 20) & 255u;
        if (family == 6u || family >= 15u)
            model += ((eax >> 16) & 15u) << 4;
        info.processor_level = (uint16_t)family;
        info.processor_revision = (uint16_t)((model << 8) | stepping);
    }
    memcpy(out, &info, sizeof info);
}
