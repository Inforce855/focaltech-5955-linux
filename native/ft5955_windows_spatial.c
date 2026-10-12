#include "ft5955_windows_spatial.h"

/* Independently authored from read-only disassembly of the matching
 * MOH FtWbioDriverUmdfV3.dll at preferred-image VA 0x180006184.
 * This is only the pre-histogram spatial step, not an image converter.
 *
 * 0x1800061a0..61c7 : clamp negative signed 16-bit words
 * 0x1800061c9..622e : replicate outermost two columns on each side
 * 0x180006230..6284 : replicate outermost first/last rows
 * 0x180006286..6374 : in-place 4-neighbour impulse correction (>50)
 *
 * Modifications occur in scan order. Do not simultaneously read neighbours
 * from a snapshot: the observed Windows routine processes in place.
 */
int
ft5955_windows_spatial_correct(uint16_t *samples, size_t count)
{
    if (samples == NULL || count != FT5955_SPATIAL_SAMPLES)
        return -1;

    for (size_t i = 0; i < count; ++i) {
        if (samples[i] & 0x8000u)
            samples[i] = 0;
    }

    for (size_t y = 0; y < FT5955_SPATIAL_HEIGHT; ++y) {
        const size_t base = y * FT5955_SPATIAL_WIDTH;
        samples[base + 1] = samples[base + 2];
        samples[base] = samples[base + 1];
        samples[base + 62] = samples[base + 61];
        samples[base + 63] = samples[base + 62];
    }

    for (size_t x = 0; x < FT5955_SPATIAL_WIDTH; ++x) {
        samples[x] = samples[FT5955_SPATIAL_WIDTH + x];
        samples[(FT5955_SPATIAL_HEIGHT - 1) * FT5955_SPATIAL_WIDTH + x] =
            samples[(FT5955_SPATIAL_HEIGHT - 2) * FT5955_SPATIAL_WIDTH + x];
    }

    /* Pixel coordinates are x=2..61 and y=2..77 inclusive. The x/y
     * loop, count comparison and 16-bit wrap match the DLL instructions. */
    for (size_t y = 2; y < FT5955_SPATIAL_HEIGHT - 2; ++y) {
        for (size_t x = 2; x < FT5955_SPATIAL_WIDTH - 2; ++x) {
            const size_t i = y * FT5955_SPATIAL_WIDTH + x;
            const uint16_t centre = samples[i];
            const uint16_t high = (uint16_t)(centre + 50u);
            const uint16_t low = centre <= 50u
                                 ? 0u : (uint16_t)(centre - 50u);
            const uint16_t neighbours[4] = {
                samples[i - 1],
                samples[i + 1],
                samples[i - FT5955_SPATIAL_WIDTH],
                samples[i + FT5955_SPATIAL_WIDTH]
            };
            unsigned above = 0;
            unsigned below = 0;
            uint16_t sum = 0;

            for (size_t n = 0; n < 4; ++n) {
                sum = (uint16_t)(sum + neighbours[n]);
                above += neighbours[n] > high;
                below += neighbours[n] < low;
            }
            if (above >= 3 || below >= 3)
                samples[i] = (uint16_t)(sum >> 2);
        }
    }
    return 0;
}
