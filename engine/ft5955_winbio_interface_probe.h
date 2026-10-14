/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic, deliberately incomplete WinBio callback-table header for MOH.
 * This is NOT a valid working Sensor/Storage adapter and cannot enable Attach.
 */
#ifndef FT5955_WINBIO_INTERFACE_PROBE_H
#define FT5955_WINBIO_INTERFACE_PROBE_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define FT5955_WINBIO_SENSOR_TYPE UINT32_C(1)
#define FT5955_WINBIO_ENGINE_TYPE UINT32_C(2)
#define FT5955_WINBIO_STORAGE_TYPE UINT32_C(3)
#define FT5955_WINBIO_PROBE_BYTES 0x100u
#define FT5955_WINBIO_PROBE_SLOTS ((FT5955_WINBIO_PROBE_BYTES - 0x20u)/8u)
typedef struct {
    uint16_t version_major, version_minor;
    uint32_t type;
    uint64_t size;
    uint8_t adapter_id[16]; /* GUID, zero until real adapter identity validated */
    uint64_t slots[FT5955_WINBIO_PROBE_SLOTS];
} ft5955_winbio_interface_probe;
_Static_assert(sizeof(ft5955_winbio_interface_probe)==0x100u,"probe table size");
_Static_assert(offsetof(ft5955_winbio_interface_probe,slots)==0x20u,"callback offset");
_Static_assert(offsetof(ft5955_winbio_interface_probe,size)==0x08u,"header Size offset");
_Static_assert(offsetof(ft5955_winbio_interface_probe,adapter_id)==0x10u,"GUID offset");
static inline void ft5955_winbio_interface_probe_init(
    ft5955_winbio_interface_probe *out, uint32_t type)
{
    memset(out,0,sizeof(*out));
    out->version_major=3;
    out->version_minor=0;
    out->type=type;
    out->size=sizeof(*out);
}
#endif
