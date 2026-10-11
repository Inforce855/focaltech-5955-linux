#include "ft_focal_cutoff.h"
#include <math.h>

int ft5955_select_cutoff_bin(const float *bins, size_t count,
                             struct ft5955_cutoff_result *result)
{
    if (!bins || !result || count != FT5955_CUTOFF_BINS)
        return -1;

    float lower = 0.0f, upper = 0.0f;
    for (size_t i = 0; i < count; ++i) {
        if (!isfinite(bins[i]) || bins[i] < 0.0f)
            return -1;
        if (i < 200u)
            lower += bins[i];
        else
            upper += bins[i];
    }
    if (!isfinite(lower) || !isfinite(upper))
        return -1;

    const unsigned tail = (double)upper > 0.8 * (double)lower;
    const float threshold = tail ? lower * 100.0f / upper : 75.0f;
    const unsigned max_window = tail ? 200u : 250u;
    const unsigned start = tail ? 190u : 240u;
    unsigned low_streak = 0;
    size_t found = FT5955_CUTOFF_BINS;

    /* Search backwards from 190 (tail mode) or 240 (normal). The first
     * above-threshold five-bin window following >=6 below-threshold windows
     * determines the cutoff. This differs from applying a fixed 80% clip. */
    for (int center = (int)start; center >= 0; --center) {
        const unsigned first = center >= 2 ? (unsigned)(center - 2) : 0u;
        unsigned last = (unsigned)(center + 2);
        if (last > max_window)
            last = max_window;
        if (last >= FT5955_CUTOFF_BINS)
            last = FT5955_CUTOFF_BINS - 1u;
        float mass = 0.0f;
        for (unsigned j = first; j <= last; ++j)
            mass += bins[j];
        if (threshold > mass) {
            ++low_streak;
        } else if (low_streak > 5u) {
            found = (size_t)center;
            break;
        } else {
            low_streak = 0u;
        }
    }

    size_t cutoff = found <= 49u ? 250u : found;
    if (!tail && cutoff < 250u) {
        cutoff += 30u;
        if (cutoff > 250u)
            cutoff = 250u;
    }
    *result = (struct ft5955_cutoff_result){
        .cutoff_bin = cutoff,
        .detected_bin = found,
        .high_tail_branch = tail,
        .lower_mass = lower,
        .upper_mass = upper,
        .window_threshold = threshold,
    };
    return 0;
}
