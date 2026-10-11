#include "ft_focal_tone_v3.h"
#include "ft_focal_histogram.h"
#include <string.h>

int ft5955_tone_v3_normalize(const int16_t *input, size_t n,
                              uint8_t *out, size_t out_size,
                              struct ft5955_tone_v3_metrics *metrics)
{
    if (!input || !out || !metrics || n != FT5955_FOCAL_PIXELS ||
        out_size != FT5955_FOCAL_PIXELS)
        return -1;

    /* The actual ELF uses 16-bit in-place negation and signed/unsigned
     * mixed reads. Its wrapped behaviour on negative words remains
     * unresolved; refuse those inputs instead of silently inventing it. */
    uint16_t minimum = UINT16_MAX;
    uint16_t maximum = 0;
    for (size_t i = 0; i < n; ++i) {
        if (input[i] < 0)
            return -2;
        const uint16_t val = (uint16_t)input[i];
        if (val < minimum) minimum = val;
        if (val > maximum) maximum = val;
    }

    *metrics = (struct ft5955_tone_v3_metrics){0};
    metrics->input_min = minimum;
    metrics->input_max = maximum;
    if (minimum == maximum) {
        memset(out, 0, out_size);
        return 1;
    }

    float hist256[FT5955_FOCAL_HIST_BINS];
    float hist250[FT5955_FOCAL_FINAL_BINS];
    struct ft5955_focal_hist_metrics histogram;
    if (ft5955_focal_histogram_research(input, n, hist256,
                                        hist250, &histogram) != 0)
        return -1;
    if (ft5955_select_cutoff_bin(hist250, FT5955_FOCAL_FINAL_BINS,
                                 &metrics->cutoff) != 0)
        return -1;

    /* Recovered FT9362 machine instructions:
     * 4f8f1..4f90a: ((cutoff_bin * shifted_max) / 250) using truncation
     * 4f91f:      add 1e-6 to denominator, converted to double
     * 4f939..4f94f: (pixel-min)*255 / denominator, trunc toward zero
     * 4f953..4f958: clamp above 255
     * In the studied positive-only domain, shifted_min=0 and
     * shifted_max=max(input)-min(input).
     */
    const uint32_t range = (uint32_t)maximum - (uint32_t)minimum;
    const uint32_t denominator_int =
        ((uint32_t)metrics->cutoff.cutoff_bin * range) / 250u;
    metrics->scaling_denominator_integer = denominator_int;
    const double denominator = (double)denominator_int + 0.000001;

    for (size_t i = 0; i < n; ++i) {
        const uint32_t inverted = (uint32_t)maximum - (uint32_t)input[i];
        const double value = (double)(inverted * 255u) / denominator;
        if (value >= 255.0) {
            out[i] = 255;
            metrics->pixels_saturated++;
        } else {
            out[i] = (uint8_t)value; /* safe: value >= 0 for input domain */
        }
    }
    return 0;
}
