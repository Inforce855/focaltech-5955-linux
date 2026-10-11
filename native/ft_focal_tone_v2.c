#include "ft_focal_tone_v2.h"

#include <string.h>

int ft5955_focal_tone_v2_research(const int16_t *samples, size_t count,
                                  uint8_t *out, size_t out_bytes,
                                  struct ft5955_tone_v2_metrics *metrics)
{
    if (!samples || !out || !metrics || count != FT5955_FOCAL_PIXELS ||
        out_bytes != FT5955_FOCAL_PIXELS)
        return -1;

    float stage256[FT5955_FOCAL_HIST_BINS];
    float stage250[FT5955_FOCAL_FINAL_BINS];
    struct ft5955_focal_hist_metrics histogram;
    const int prep = ft5955_focal_histogram_research(samples, count,
                                                     stage256, stage250, &histogram);
    if (prep < 0)
        return -1;
    *metrics = (struct ft5955_tone_v2_metrics){0};
    metrics->inverted_min = histogram.source_min;
    metrics->inverted_max = histogram.source_max;
    if (prep == 1) {
        memset(out, 0, out_bytes);
        return 1;
    }

    if (ft5955_select_cutoff_bin(stage250, FT5955_FOCAL_FINAL_BINS,
                                 &metrics->cutoff) != 0)
        return -1;

    const uint32_t range = (uint32_t)(histogram.source_max - histogram.source_min);
    /* The native ELF maps cutoff_bin * the 16-bit range / 250. For normal
     * positive samples the adjusted minimum is zero; signed extremes and
     * wrapping in the original are deliberately not reproduced. */
    const uint32_t effective = (range * (uint32_t)metrics->cutoff.cutoff_bin) / 250u;
    metrics->dynamic_range = range;
    metrics->effective_range = effective;
    if (!effective) {
        memset(out, 0, out_bytes);
        return 1;
    }

    for (size_t i = 0; i < count; ++i) {
        const uint32_t level = (uint32_t)(-((int32_t)samples[i]) - histogram.source_min);
        if (level >= effective) {
            out[i] = 255;
            ++metrics->pixels_saturated;
        } else {
            out[i] = (uint8_t)((level * 255u) / effective);
        }
    }
    return 0;
}
