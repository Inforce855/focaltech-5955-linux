#include "ft_histogram.h"

#include <stdint.h>

int ft5955_smooth_histogram(const uint32_t *input, float *output,
                            size_t bins, unsigned passes)
{
    if (!input || !output || !bins || bins > FT5955_HIST_BINS || passes > 3u)
        return -1;

    float a[FT5955_HIST_BINS];
    float b[FT5955_HIST_BINS];
    for (size_t i = 0; i < bins; ++i)
        a[i] = (float)input[i];

    for (unsigned step = 0; step < passes; ++step) {
        for (size_t i = 0; i < bins; ++i) {
            const size_t first = i > 2u ? i - 2u : 0u;
            const size_t last = i + 2u < bins ? i + 2u : bins - 1u;
            float sum = 0.0f;
            for (size_t j = first; j <= last; ++j)
                sum += a[j];
            b[i] = sum / (float)(last - first + 1u);
        }
        for (size_t i = 0; i < bins; ++i)
            a[i] = b[i];
    }

    for (size_t i = 0; i < bins; ++i)
        output[i] = a[i];
    return 0;
}
