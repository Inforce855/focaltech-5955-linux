/* Offline FocalTech 5955 normalisation bridge.
 * Reads exactly 10240 bytes of LITTLE-ENDIAN raw signed-word samples from
 * stdin; writes exactly 5120 bytes of experimental vendor-style grayscale
 * to stdout. No USB, input files, privilege changes or authentication.
 * Any stderr text is an aggregate error only, NEVER personal pixels.
 */
#include "ft_focal_tone_v3.h"

#include <stdint.h>
#include <stdio.h>

#define RAW_BYTES (FT5955_FOCAL_PIXELS * 2u)

int main(void)
{
    uint8_t raw[RAW_BYTES];
    int16_t samples[FT5955_FOCAL_PIXELS];
    uint8_t pixels[FT5955_FOCAL_PIXELS];
    struct ft5955_tone_v3_metrics metrics;

    if (fread(raw, 1, sizeof raw, stdin) != sizeof raw ||
        fgetc(stdin) != EOF) {
        fputs("Expected exactly 10240 little-endian raw bytes on stdin.\n", stderr);
        return 2;
    }

    for (size_t i = 0; i < FT5955_FOCAL_PIXELS; ++i) {
        const uint16_t raw_word = (uint16_t)raw[i * 2u] |
                                  (uint16_t)((uint16_t)raw[i * 2u + 1u] << 8u);
        /* The existing FT5955 v3 model only covers nonnegative signed words.
         * Reject unexpected input instead of guessing sensor calibration. */
        if (raw_word > INT16_MAX) {
            fputs("Capture has unsupported signed-negative words; no output.\n", stderr);
            return 3;
        }
        samples[i] = (int16_t)raw_word;
    }

    const int status = ft5955_tone_v3_normalize(
        samples, FT5955_FOCAL_PIXELS, pixels, sizeof pixels, &metrics);
    if (status != 0) {
        fputs(status == 1 ? "Low-detail/flat capture; no output.\n" :
                            "Experimental normalizer rejected capture.\n", stderr);
        return 4;
    }

    if (fwrite(pixels, 1, sizeof pixels, stdout) != sizeof pixels) {
        fputs("Unable to write grayscale bytes to stdout.\n", stderr);
        return 5;
    }
    return 0;
}
