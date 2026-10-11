#include "ft_image.h"

#include <string.h>

/* Stable integer-valued histogram quantile, without a floating-point or
 * third-party dependency. We histogram the 16-bit contrast-inverted values
 * exactly, rather than making a premature 256-level choice. */
static uint16_t quantile_from_histogram(const uint32_t *hist, uint32_t rank)
{
    uint32_t cumulative = 0;
    for (uint32_t i = 0; i < 65536u; ++i) {
        cumulative += hist[i];
        if (cumulative > rank)
            return (uint16_t)i;
    }
    return UINT16_MAX;
}

int ft5955_prepare_image(const uint8_t *raw, size_t raw_bytes,
                         uint8_t *output, size_t output_bytes,
                         struct ft5955_image_metrics *metrics)
{
    /* Never dereference a pointer or write to output on malformed lengths. */
    if (!raw || !output || !metrics || raw_bytes != FT5955_RAW_BYTES ||
        output_bytes != FT5955_PIXELS)
        return FT5955_BAD_INPUT;

    uint16_t input[FT5955_PIXELS];
    uint16_t inverted[FT5955_PIXELS];
    uint16_t maximum = 0;
    uint32_t clamped = 0;
    for (size_t i = 0; i < FT5955_PIXELS; ++i) {
        const size_t offset = i * 2u;
        const uint16_t word = (uint16_t)raw[offset] |
                              (uint16_t)((uint16_t)raw[offset + 1u] << 8u);
        /* The Windows 5955 converter was observed to clamp signed negatives.
         * Our existing private measurements had 0% such words. */
        const uint16_t sample = word >= UINT16_C(32768) ? 0 : word;
        clamped += word >= UINT16_C(32768);
        input[i] = sample;
        if (sample > maximum)
            maximum = sample;
    }

    /* Equivalent to (signed 16-bit negate + subtract minimum) on the normal
     * non-negative sample domain. This explicitly does NOT perform a 90-degree
     * rotation, transpose or reshape: consecutive 64-word runs are rows. */
    uint32_t histogram[65536] = {0};
    for (size_t i = 0; i < FT5955_PIXELS; ++i) {
        const uint16_t value = (uint16_t)(maximum - input[i]);
        inverted[i] = value;
        histogram[value]++;
    }

    const uint16_t low = quantile_from_histogram(histogram,
                                                 (FT5955_PIXELS - 1u) / 100u);
    const uint16_t high = quantile_from_histogram(histogram,
                                              ((FT5955_PIXELS - 1u) * 99u) / 100u);
    uint32_t occupied = 0;
    uint32_t peak = 0;
    for (uint32_t bin = 0; bin <= maximum; ++bin) {
        occupied += histogram[bin] != 0;
        if (histogram[bin] > peak)
            peak = histogram[bin];
    }

    *metrics = (struct ft5955_image_metrics){
        .raw_max = maximum,
        .foreground_low = low,
        .foreground_high = high,
        .clipped_negative_words = clamped,
        .bins_with_samples = occupied,
        .peak_bin_count = peak,
    };

    /* Contrast threshold is a diagnostic guard, NOT an auth decision.
     * Empty/flat frames should never be stretched into an apparent ridge map. */
    if (high <= low || (uint32_t)(high - low) < 16u) {
        memset(output, 0, FT5955_PIXELS);
        return FT5955_LOW_CONTRAST;
    }

    const uint32_t span = (uint32_t)(high - low);
    for (size_t i = 0; i < FT5955_PIXELS; ++i) {
        const uint32_t value = inverted[i];
        if (value <= low) output[i] = 0;
        else if (value >= high) output[i] = 255;
        else output[i] = (uint8_t)(((value - low) * 255u + span / 2u) / span);
    }
    return FT5955_OK;
}
