/* Entirely synthetic histogram tests. No fingerprint data. */
#include "ft_histogram.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static int near(float x, float y)
{
    return fabsf(x - y) < 0.0001f;
}

static void test_invalid_inputs(void)
{
    uint32_t counts[FT5955_HIST_BINS] = {0};
    float output[FT5955_HIST_BINS] = {0};
    assert(ft5955_smooth_histogram(NULL, output, 256, 3) == -1);
    assert(ft5955_smooth_histogram(counts, NULL, 256, 3) == -1);
    assert(ft5955_smooth_histogram(counts, output, 0, 3) == -1);
    assert(ft5955_smooth_histogram(counts, output, 257, 3) == -1);
    assert(ft5955_smooth_histogram(counts, output, 256, 4) == -1);
}

static void test_constant_bins(void)
{
    uint32_t counts[FT5955_HIST_BINS];
    float output[FT5955_HIST_BINS];
    for (size_t i = 0; i < FT5955_HIST_BINS; ++i)
        counts[i] = 42;
    assert(ft5955_smooth_histogram(counts, output, 256, 3) == 0);
    for (size_t i = 0; i < FT5955_HIST_BINS; ++i)
        assert(near(output[i], 42.0f));
}

static void test_impulse_and_three_passes(void)
{
    uint32_t counts[FT5955_HIST_BINS] = {0};
    float output[FT5955_HIST_BINS];
    counts[128] = 125;
    assert(ft5955_smooth_histogram(counts, output, 256, 1) == 0);
    assert(near(output[128], 25.0f));
    assert(near(output[127], 25.0f));
    assert(near(output[125], 0.0f));
    assert(ft5955_smooth_histogram(counts, output, 256, 3) == 0);
    assert(near(output[128], 19.0f));
    assert(near(output[127], 18.0f));
    assert(near(output[121], 0.0f));
}

static void test_boundary_and_250_bin_window(void)
{
    uint32_t counts[FT5955_HIST_BINS] = {0};
    float output[FT5955_HIST_BINS];
    counts[0] = 125;
    counts[249] = 250;
    assert(ft5955_smooth_histogram(counts, output, 250, 3) == 0);
    for (size_t i = 0; i < 250; ++i)
        assert(isfinite(output[i]) && output[i] >= 0.0f);
    assert(output[0] > output[10]);
    assert(output[249] > output[239]);
}

static void test_determinism_and_no_mutation(void)
{
    uint32_t counts[FT5955_HIST_BINS];
    uint32_t original[FT5955_HIST_BINS];
    float a[FT5955_HIST_BINS], b[FT5955_HIST_BINS];
    for (size_t i = 0; i < FT5955_HIST_BINS; ++i)
        counts[i] = (uint32_t)((i * 17u + i * i) % 101u);
    memcpy(original, counts, sizeof counts);
    assert(ft5955_smooth_histogram(counts, a, 256, 3) == 0);
    assert(ft5955_smooth_histogram(counts, b, 256, 3) == 0);
    assert(memcmp(original, counts, sizeof counts) == 0);
    assert(memcmp(a, b, sizeof a) == 0);
}

int main(void)
{
    test_invalid_inputs();
    test_constant_bins();
    test_impulse_and_three_passes();
    test_boundary_and_250_bin_window();
    test_determinism_and_no_mutation();
    puts("PASS: 5 synthetic-only FocalTech histogram-smoothing tests");
    puts("No biometric data, USB access, vendor library execution or OS settings changed.");
    return 0;
}
