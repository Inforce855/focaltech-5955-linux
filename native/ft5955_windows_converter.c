#include "ft5955_windows_converter.h"
#include <math.h>
#include <string.h>
#include <limits.h>

/* Exact MOH DLL preferred-image virtual addresses are recorded as evidence.
 * This implements the 64x80 Windows general converter at 0x180005C78,
 * independently from read-only disassembly (no proprietary code included).
 * It is a synthetic-tested research prototype, NOT a proven bit-identical
 * converter and NOT connected to libfprint or the Windows authentication path.
 */

/* 0x1800060A8: one clipped 1D radius-two moving-average pass.
 * This temporary-copy behaviour is important (not in-place smoothing).
 */
static void smooth(float *hist, size_t n)
{
    float tmp[256];
    for (size_t i = 0; i < n; ++i) {
        const size_t lo = i > 2 ? i - 2 : 0;
        const size_t hi = i + 2 < n ? i + 2 : n - 1;
        float sum = 0.0f;
        for (size_t j = lo; j <= hi; ++j)
            sum += hist[j];
        tmp[i] = sum / (float)(hi - lo + 1);
    }
    memcpy(hist, tmp, n * sizeof(hist[0]));
}

/* 0x180005EE2..5FC6: adaptive histogram cutoff (all arithmetic floats
 * except the integer search window). Note: threshold comparison is
 * against SUM OF FIVE BINS, not their average.
 */
static int choose_cutoff(const float *h)
{
    float lower = 0.0f, upper = 0.0f;
    for (int i = 0; i <= 199; ++i)
        lower += h[i];
    for (int i = 200; i <= 249; ++i)
        upper += h[i];

    const int start = (double)upper > (double)lower * 0.8 ? 200 : 250;
    const float threshold = start == 200 ? (lower * 100.0f) / upper : 75.0f;
    int cutoff = start;
    int n_low_windows = 0;
    int j = start - 10;
    int end = j + 2;

    while (j >= 0) {
        int lo = end - 4;
        if (lo < 0) lo = 0;
        int hi = end < start ? end : start;
        float window = 0.0f;
        for (int k = lo; k <= hi; ++k)
            window += h[k];
        if (threshold > window) {
            ++n_low_windows;
        } else {
            if (n_low_windows > 5) {
                cutoff = j;
                break;
            }
            n_low_windows = 0;
        }
        --j;
        --end;
    }
    if (cutoff < 50)
        cutoff = 250;
    if (start == 250) {
        cutoff += 30;
        if (cutoff > 250) cutoff = 250;
    }
    return cutoff;
}

int ft5955_windows_convert(const uint8_t *raw_le, size_t raw_size,
                           uint8_t *out, size_t out_size,
                           struct ft5955_windows_convert_stats *stats)
{
    if (!raw_le || !out || !stats || raw_size != FT5955_RAW_BYTES ||
        out_size != FT5955_IMAGE_BYTES)
        return -1;
    *stats = (struct ft5955_windows_convert_stats){0};
    memset(out, 0, out_size);

    uint16_t pixels[FT5955_SPATIAL_SAMPLES];
    for (size_t i = 0; i < FT5955_SPATIAL_SAMPLES; ++i)
        pixels[i] = (uint16_t)((uint16_t)raw_le[2*i] |
                    ((uint16_t)raw_le[2*i+1] << 8));

    if (ft5955_windows_spatial_correct(pixels, FT5955_SPATIAL_SAMPLES))
        return -1;

    /* 0x180005CB1..5CF1: negate as 16-bit, find SIGNED minimum,
     * subtract minimum as 16-bit. All arithmetic intentionally wraps.
     */
    int min = INT16_MAX;
    for (size_t i = 0; i < FT5955_SPATIAL_SAMPLES; ++i) {
        pixels[i] = (uint16_t)(0u - pixels[i]);
        const int v = (int16_t)pixels[i];
        if (v < min) min = v;
    }
    int shifted_min = INT16_MAX;
    int shifted_max = INT16_MIN;
    for (size_t i = 0; i < FT5955_SPATIAL_SAMPLES; ++i) {
        pixels[i] = (uint16_t)(pixels[i] - (uint16_t)min);
        const int v = (int16_t)pixels[i];
        if (v < shifted_min) shifted_min = v;
        if (v > shifted_max) shifted_max = v;
    }
    stats->shifted_min = (int16_t)shifted_min;
    stats->shifted_max = (int16_t)shifted_max;
    const int range = shifted_max - shifted_min;
    if (range == 0) return 1;

    /* 0x180005D24..5DAB: histogram over 256 bins, floating point epsilon
     * is the actual DLL .rdata value 0x18001AFF0 = 0.000001.
     */
    uint32_t counts[256] = {0};
    const double hist_denominator = (double)range + 0.000001;
    for (size_t i = 0; i < FT5955_SPATIAL_SAMPLES; ++i) {
        const int shifted = (int16_t)pixels[i];
        const int index = (int)((double)((shifted - shifted_min) << 8) /
                                hist_denominator);
        if (index < 0 || index >= 256)
            return -2;
        ++counts[index];
    }

    /* 0x180005DAD..5EDD: three radius-2 float smooths of 256 counts,
     * followed by a 250-bin copy and two more identical smooths.
     */
    float hist[256];
    for (size_t i = 0; i < 256; ++i)
        hist[i] = (float)counts[i];
    for (int i = 0; i < 3; ++i)
        smooth(hist, 256);
    for (int i = 0; i < 2; ++i)
        smooth(hist, 250);

    const int cutoff = choose_cutoff(hist);
    stats->cutoff_bin = cutoff;

    /* 0x180005FCA..5FDF: imul then MSVC signed divide by 250,
     * using a multiply-by-reciprocal instruction sequence.
     */
    const int divisor = (cutoff * shifted_max) / 250 - shifted_min;
    stats->scale_denominator = divisor;
    if (divisor <= 0)
        return -2;

    /* 0x180005FE4..602F: cvttsd2si (trunc toward zero) of (pixel-min)*255
     * divided by (scale + epsilon), clamp values above 255. The original
     * code does not clamp negative output; avoid silent wrap with an error.
     */
    for (size_t i = 0; i < FT5955_SPATIAL_SAMPLES; ++i) {
        const int v = (int16_t)pixels[i] - shifted_min;
        const double scaled = (double)(v * 255) / ((double)divisor + 0.000001);
        if (!isfinite(scaled) || scaled < 0.0 || scaled > (double)INT_MAX)
            return -2;
        int result = (int)scaled;
        if (result > 255) {
            result = 255;
            ++stats->saturated_pixels;
        }
        out[i] = (uint8_t)result;
    }
    return 0;
}
