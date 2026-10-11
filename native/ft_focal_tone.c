#include "ft_focal_tone.h"

#include <string.h>

int ft5955_focal_tone_research(const int16_t *samples, size_t count,
                               uint8_t *out, size_t out_bytes,
                               struct ft5955_focal_tone_metrics *metrics)
{
    if (!samples || !out || !metrics || count != FT5955_FOCAL_PIXELS ||
        out_bytes != FT5955_FOCAL_PIXELS)
        return -1;

    float hist256[FT5955_FOCAL_HIST_BINS];
    float hist250[FT5955_FOCAL_FINAL_BINS];
    struct ft5955_focal_hist_metrics hist_metrics;
    const int status = ft5955_focal_histogram_research(samples, count, hist256,
                                                       hist250, &hist_metrics);
    if (status < 0)
        return -1;

    *metrics = (struct ft5955_focal_tone_metrics){0};
    metrics->negated_min = hist_metrics.source_min;
    metrics->negated_max = hist_metrics.source_max;
    if (status == 1) {
        memset(out, 0, out_bytes);
        return 1;
    }

    /* Disassembly: upper histogram mass > 0.8 * lower mass selects a
     * 200/250 contrast cap, otherwise the full 250/250 cap. Intermediate
     * arithmetic is kept at 32 bits to avoid signed INT16_MIN overflow.
     * Real FT9362 has additional signed-word and scanning behaviour that
     * remains unverified; this is an independent approximation. */
    const uint32_t span = (uint32_t)(hist_metrics.source_max - hist_metrics.source_min);
    const uint16_t numerator = hist_metrics.high_tail_branch ? 200u : 250u;
    const uint32_t limit = (span * numerator) / 250u;
    metrics->high_tail_branch = hist_metrics.high_tail_branch;
    metrics->contrast_fraction_of_250 = numerator;
    metrics->contrast_limit = limit;
    if (limit == 0u) {
        memset(out, 0, out_bytes);
        return 1;
    }

    for (size_t i = 0; i < count; ++i) {
        const uint32_t level = (uint32_t)(-((int32_t)samples[i]) - hist_metrics.source_min);
        if (level >= limit) {
            out[i] = UINT8_MAX;
            ++metrics->saturated_count;
        } else {
            out[i] = (uint8_t)((level * 255u) / limit);
        }
    }
    return 0;
}
