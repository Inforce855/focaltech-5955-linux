/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Windows x64 SYSTEM_INFO (48 bytes) subset for a guarded MOH experiment.
 * Standalone ABI layout, independent of Windows SDK headers.
 */
#ifndef FT5955_COMPAT_SYSINFO_H
#define FT5955_COMPAT_SYSINFO_H
#include <stddef.h>
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_SYSINFO_MS __attribute__((ms_abi))
#else
#error The MOH bridge requires x86-64 GCC/Clang
#endif
typedef struct ft5955_system_info {
    uint16_t processor_architecture;
    uint16_t reserved;
    uint32_t page_size;
    void *minimum_application_address;
    void *maximum_application_address;
    uintptr_t active_processor_mask;
    uint32_t number_of_processors;
    uint32_t processor_type;
    uint32_t allocation_granularity;
    uint16_t processor_level;
    uint16_t processor_revision;
} ft5955_system_info;
_Static_assert(sizeof(ft5955_system_info) == 48, "Windows x64 SYSTEM_INFO must be 48 bytes");
_Static_assert(offsetof(ft5955_system_info, page_size) == 4, "SYSTEM_INFO page size offset");
_Static_assert(offsetof(ft5955_system_info, minimum_application_address) == 8, "SYSTEM_INFO min addr offset");
_Static_assert(offsetof(ft5955_system_info, maximum_application_address) == 16, "SYSTEM_INFO max addr offset");
_Static_assert(offsetof(ft5955_system_info, active_processor_mask) == 24, "SYSTEM_INFO processor mask offset");
_Static_assert(offsetof(ft5955_system_info, number_of_processors) == 32, "SYSTEM_INFO processor count offset");
_Static_assert(offsetof(ft5955_system_info, allocation_granularity) == 40, "SYSTEM_INFO allocation granularity offset");
_Static_assert(offsetof(ft5955_system_info, processor_revision) == 46, "SYSTEM_INFO revision offset");
void FT5955_SYSINFO_MS ft5955_GetSystemInfo(ft5955_system_info *out);
#endif
