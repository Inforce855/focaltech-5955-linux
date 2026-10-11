/* Synthetic regression tests for the FT9362-derived experimental tone map. */
#include "ft_focal_tone.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_bad_arguments(void)
{
    int16_t samples[FT5955_FOCAL_PIXELS] = {0};
    uint8_t out[FT5955_FOCAL_PIXELS];
    struct ft5955_focal_tone_metrics m;
    memset(out, 0x5a, sizeof out);
    assert(ft5955_focal_tone_research(NULL, 5120, out, 5120, &m) == -1);
    assert(ft5955_focal_tone_research(samples, 5119, out, 5120, &m) == -1);
    assert(ft5955_focal_tone_research(samples, 5120, out, 5119, &m) == -1);
    assert(ft5955_focal_tone_research(samples, 5120, NULL, 5120, &m) == -1);
    assert(ft5955_focal_tone_research(samples, 5120, out, 5120, NULL) == -1);
    assert(out[0] == 0x5a);
}

static void test_flat_image(void)
{
    int16_t samples[FT5955_FOCAL_PIXELS];
    uint8_t out[FT5955_FOCAL_PIXELS];
    struct ft5955_focal_tone_metrics m;
    for (size_t i = 0; i < FT5955_FOCAL_PIXELS; ++i) samples[i] = 1111;
    memset(out, 1, sizeof out);
    assert(ft5955_focal_tone_research(samples, 5120, out, 5120, &m) == 1);
    assert(m.negated_min == -1111 && m.negated_max == -1111);
    for (size_t i = 0; i < FT5955_FOCAL_PIXELS; ++i) assert(out[i] == 0);
}

static void test_even_ramp_uses_full_range(void)
{
    int16_t samples[FT5955_FOCAL_PIXELS];
    uint8_t out[FT5955_FOCAL_PIXELS];
    struct ft5955_focal_tone_metrics m;
    for (size_t i = 0; i < FT5955_FOCAL_PIXELS; ++i)
        samples[i] = (int16_t)(i % 1024u);
    assert(ft5955_focal_tone_research(samples, 5120, out, 5120, &m) == 0);
    assert(m.high_tail_branch == 0);
    assert(m.contrast_fraction_of_250 == 250);
    assert(m.contrast_limit == 1023);
    assert(out[0] == 255 && out[1023] == 0);
    assert(out[500] > out[800]);
}

static void test_high_tail_branch_compresses_limit(void)
{
    int16_t samples[FT5955_FOCAL_PIXELS];
    uint8_t out[FT5955_FOCAL_PIXELS];
    struct ft5955_focal_tone_metrics m;
    /* Majority at inverted histogram bin 220; bin 255 is dropped by
     * FocalTech's second 250-bin smoothing window. */
    for (size_t i = 0; i < FT5955_FOCAL_PIXELS; ++i)
        samples[i] = (i < 4000u) ? 140 : 1000;
    samples[3] = 0; /* establish full dynamic range */
    samples[1] = 200;
    samples[2] = 500;
    assert(ft5955_focal_tone_research(samples, 5120, out, 5120, &m) == 0);
    assert(m.high_tail_branch == 1);
    assert(m.contrast_fraction_of_250 == 200);
    assert(m.contrast_limit == 800);
    assert(out[0] == 255 && out[1] == 255 && out[2] < 255);
    assert(out[4000] == 0);
    assert(m.saturated_count > 3000);
}

static void test_signed_extremes_determinism_no_mutation(void)
{
    int16_t samples[FT5955_FOCAL_PIXELS], original[FT5955_FOCAL_PIXELS];
    uint8_t a[FT5955_FOCAL_PIXELS], b[FT5955_FOCAL_PIXELS];
    struct ft5955_focal_tone_metrics ma, mb;
    for (size_t i = 0; i < FT5955_FOCAL_PIXELS; ++i)
        samples[i] = (int16_t)((i * 37u) % 32760u);
    samples[0] = INT16_MIN;
    samples[1] = INT16_MAX;
    memcpy(original, samples, sizeof samples);
    assert(ft5955_focal_tone_research(samples, 5120, a, 5120, &ma) == 0);
    assert(ft5955_focal_tone_research(samples, 5120, b, 5120, &mb) == 0);
    assert(memcmp(samples, original, sizeof samples) == 0);
    assert(memcmp(a, b, sizeof a) == 0);
    assert(memcmp(&ma, &mb, sizeof ma) == 0);
}

int main(void)
{
    test_bad_arguments();
    test_flat_image();
    test_even_ramp_uses_full_range();
    test_high_tail_branch_compresses_limit();
    test_signed_extremes_determinism_no_mutation();
    puts("PASS: 5 synthetic-only FocalTech tone-mapping research tests");
    puts("No USB access, biometric images, vendor binaries or OS changes.");
    return 0;
}
