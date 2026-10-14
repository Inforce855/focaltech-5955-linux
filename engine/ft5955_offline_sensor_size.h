/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Offline-only sensor-size IOCTL simulator. NEVER for production use.
 * The MOH Attach disassembly invokes DeviceIoControl with code 0x442018
 * and a two-byte output buffer. The returned width and height here are
 * explicitly SYNTHETIC, not confirmed physical FT5955 sensor dimensions.
 */
#ifndef FT5955_OFFLINE_SENSOR_SIZE_H
#define FT5955_OFFLINE_SENSOR_SIZE_H
#include <stdint.h>
#include <stddef.h>
#define FT5955_IOCTL_BIOMETRIC_SENSOR_SIZE UINT32_C(0x00442018)
#define FT5955_SIM_WIDTH UINT8_C(64)
#define FT5955_SIM_HEIGHT UINT8_C(80)
static inline int ft5955_sim_sensor_ioctl(uint32_t code, void *out,
                                          uint32_t outlen, uint32_t *returned) {
    if (returned) *returned=0;
    if(code!=FT5955_IOCTL_BIOMETRIC_SENSOR_SIZE || !out || outlen<2u)
        return 0;
    ((uint8_t*)out)[0]=FT5955_SIM_WIDTH;
    ((uint8_t*)out)[1]=FT5955_SIM_HEIGHT;
    if(returned) *returned=2;
    return 1;
}
#endif
