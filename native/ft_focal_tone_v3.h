/* Offline research-only normalisation derived from FT9362 Linux ELF arithmetic.
 * No vendor library loading or execution, USB, files or authentication.
 * Only the observed nonnegative sample domain of FocalTech 5955 is accepted.
 */
#ifndef FT5955_FOCAL_TONE_V3_H
#define FT5955_FOCAL_TONE_V3_H
#include <stddef.h>
#include <stdint.h>
#include "ft_focal_cutoff.h"

struct ft5955_tone_v3_metrics {
    uint16_t input_min, input_max;
    uint32_t scaling_denominator_integer;
    uint32_t pixels_saturated;
    struct ft5955_cutoff_result cutoff;
};

/* 0 success, 1 flat image, -1 invalid sizes/pointers, -2 out of studied
 * signed-word domain. Output written only on success or flat image.
 * Not a validated 5955 vendor transform or a fingerprint matcher.
 */
int ft5955_tone_v3_normalize(const int16_t *input, size_t n,
                              uint8_t *out, size_t out_size,
                              struct ft5955_tone_v3_metrics *metrics);
#endif
