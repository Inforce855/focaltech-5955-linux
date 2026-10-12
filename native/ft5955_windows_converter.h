/* Independent research reconstruction of FocalTech 5955 MOH 64x80 converter.
 * No USB access, no vendor DLL loading, no Windows Hello, no biometrics saved.
 * Windows VA: 0x180005C78; the output has NOT yet been compared against
 * the running proprietary DLL. See docs/windows-moh-image-conversion-2026-10-12.md.
 */
#ifndef FT5955_WINDOWS_CONVERTER_H
#define FT5955_WINDOWS_CONVERTER_H
#include <stddef.h>
#include <stdint.h>
#include "ft5955_windows_spatial.h"

#define FT5955_RAW_BYTES (FT5955_SPATIAL_SAMPLES * 2u)
#define FT5955_IMAGE_BYTES FT5955_SPATIAL_SAMPLES

struct ft5955_windows_convert_stats {
    int16_t shifted_min;
    int16_t shifted_max;
    int cutoff_bin;
    int scale_denominator;
    uint32_t saturated_pixels;
};

/* The 10240-byte input is LE signed-16 raw sensor data, no protocol framing.
 *  0 = converted
 *  1 = uniform/no usable contrast; 8-bit result is entirely zero
 * -1 = invalid pointer/size
 * -2 = value / index outside safely reconstructed processing domain
 * No files, network operations or device access. Caller owns all buffers. */
int ft5955_windows_convert(const uint8_t *raw_le, size_t raw_size,
                           uint8_t *out, size_t out_size,
                           struct ft5955_windows_convert_stats *stats);

#endif
