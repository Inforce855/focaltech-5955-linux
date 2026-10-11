/* Independent, offline image preparation prototype for FocalTech 2808:5955.
 * No USB, disk I/O, network, biometric enrolment or authentication API.
 * 64 columns x 80 rows, 5120 little-endian unsigned 16-bit samples.
 * This is NOT a validated reproduction of the proprietary algorithm.
 */
#ifndef FT5955_IMAGE_H
#define FT5955_IMAGE_H

#include <stddef.h>
#include <stdint.h>

#define FT5955_WIDTH 64u
#define FT5955_HEIGHT 80u
#define FT5955_PIXELS (FT5955_WIDTH * FT5955_HEIGHT)
#define FT5955_RAW_BYTES (FT5955_PIXELS * 2u)

/* Low-contrast images are rejected, rather than creating false features. */
enum ft5955_result {
    FT5955_OK = 0,
    FT5955_LOW_CONTRAST = 1,
    FT5955_BAD_INPUT = -1
};

struct ft5955_image_metrics {
    uint16_t raw_max;
    uint16_t foreground_low;  /* percentile of polarity-inverted 16-bit samples */
    uint16_t foreground_high;
    uint32_t clipped_negative_words;
    uint32_t bins_with_samples;
    uint32_t peak_bin_count;
};

/* A deterministic, provisional 8-bit preview transformation.
 * All inputs read as little-endian unsigned words, with values above INT16_MAX
 * clamped to zero, consistent with the observed Windows input clamp.
 * The observed native Linux negation + subtraction maps to max(input)-input
 * for nonnegative samples. The robust 1/99-percentile contrast step below is
 * OUR diagnostic approximation, not a confirmed vendor algorithm.
 * Returns LOW_CONTRAST with a zeroed output for unsuitable flat input.
 * No memory allocation, writes to files, or mutated raw input.
 */
int ft5955_prepare_image(const uint8_t *raw, size_t raw_bytes,
                         uint8_t *output, size_t output_bytes,
                         struct ft5955_image_metrics *metrics);

#endif
