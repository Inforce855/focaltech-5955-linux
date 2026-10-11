/* Offline experimental FT9362-derived cut-off tone mapper; not an authenticator. */
#ifndef FT5955_FOCAL_TONE_V2_H
#define FT5955_FOCAL_TONE_V2_H
#include <stddef.h>
#include <stdint.h>
#include "ft_focal_cutoff.h"
#include "ft_focal_histogram.h"

struct ft5955_tone_v2_metrics {
    int32_t inverted_min;
    int32_t inverted_max;
    uint32_t dynamic_range;
    uint32_t effective_range;
    uint32_t pixels_saturated;
    struct ft5955_cutoff_result cutoff;
};

/* 5120 native int16 words, 5120 output bytes; 0 OK, 1 constant frame,
 * -1 bad inputs; never writes into samples, never uses USB or files.
 * This independently models some observed FT9362 histogram and tone stages.
 * It has NOT been validated against vendor pixel output on 5955 hardware.
 */
int ft5955_focal_tone_v2_research(const int16_t *samples, size_t count,
                                  uint8_t *out, size_t out_bytes,
                                  struct ft5955_tone_v2_metrics *metrics);
#endif
