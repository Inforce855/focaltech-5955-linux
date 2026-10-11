#include "ft_focal_histogram.h"
#include "ft_histogram.h"

#include <math.h>
#include <string.h>

int ft5955_focal_histogram_research(const int16_t *pixels, size_t count,
                                    float output256[FT5955_FOCAL_HIST_BINS],
                                    float output250[FT5955_FOCAL_FINAL_BINS],
                                    struct ft5955_focal_hist_metrics *metrics)
{
    if (!pixels || !output256 || !output250 || !metrics ||
        count != FT5955_FOCAL_PIXELS)
        return -1;

    /* The native FocalTech build negates signed words, offsets by their
     * minimum, and bins into 256 proportional levels. Perform intermediate
     * operations in signed 32-bit arithmetic so INT16_MIN is safe. */
    int32_t low = -((int32_t)pixels[0]);
    int32_t high = low;
    for (size_t i = 1; i < count; ++i) {
        const int32_t sample = -((int32_t)pixels[i]);
        if (sample < low) low = sample;
        if (sample > high) high = sample;
    }

    *metrics = (struct ft5955_focal_hist_metrics){0};
    metrics->source_min = low;
    metrics->source_max = high;
    for (size_t i = 0; i < FT5955_FOCAL_HIST_BINS; ++i)
        output256[i] = 0.0f;
    for (size_t i = 0; i < FT5955_FOCAL_FINAL_BINS; ++i)
        output250[i] = 0.0f;

    if (high <= low)
        return 1;

    /* The reference uses (range + 1e-6), a 256x factor and truncation.
     * Bound bin indices in our own implementation for robust memory safety. */
    const double denom = (double)(high - low) + 0.000001;
    for (size_t i = 0; i < count; ++i) {
        const int32_t sample = -((int32_t)pixels[i]);
        const double scaled = ((double)(sample - low) * 256.0) / denom;
        const size_t bin = scaled >= 255.0 ? 255u : (size_t)scaled;
        ++metrics->raw_histogram[bin];
    }

    if (ft5955_smooth_histogram(metrics->raw_histogram, output256,
                                FT5955_FOCAL_HIST_BINS, 3u) != 0)
        return -1;
    if (ft5955_smooth_histogram_f32(output256, output250,
                                    FT5955_FOCAL_FINAL_BINS, 2u) != 0)
        return -1;
    for (size_t i = 0; i < 200u; ++i)
        metrics->lower_mass += output250[i];
    for (size_t i = 200u; i < FT5955_FOCAL_FINAL_BINS; ++i)
        metrics->upper_mass += output250[i];
    metrics->high_tail_branch =
        (double)metrics->upper_mass > 0.8 * (double)metrics->lower_mass;
    return 0;
}
