#include "ft_focal_histogram.h"
#include "ft_histogram.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static void test_reject_invalid(void)
{
    int16_t pixels[FT5955_FOCAL_PIXELS] = {0};
    float hist256[256], hist250[250];
    struct ft5955_focal_hist_metrics m;
    assert(ft5955_focal_histogram_research(NULL, 5120, hist256, hist250, &m) == -1);
    assert(ft5955_focal_histogram_research(pixels, 5119, hist256, hist250, &m) == -1);
    assert(ft5955_focal_histogram_research(pixels, 5120, NULL, hist250, &m) == -1);
    assert(ft5955_focal_histogram_research(pixels, 5120, hist256, NULL, &m) == -1);
    assert(ft5955_focal_histogram_research(pixels, 5120, hist256, hist250, NULL) == -1);
}

static void test_reject_flat(void)
{
    int16_t pixels[FT5955_FOCAL_PIXELS];
    float hist256[256], hist250[250];
    struct ft5955_focal_hist_metrics m;
    for (size_t i = 0; i < 5120; ++i) pixels[i] = 1234;
    assert(ft5955_focal_histogram_research(pixels, 5120, hist256, hist250, &m) == 1);
    assert(m.source_min == -1234 && m.source_max == -1234);
    assert(m.lower_mass == 0.0f && m.upper_mass == 0.0f);
}

static void test_two_levels_and_mass(void)
{
    int16_t pixels[FT5955_FOCAL_PIXELS];
    float hist256[256], hist250[250];
    struct ft5955_focal_hist_metrics m;
    for (size_t i = 0; i < 5120; ++i) pixels[i] = (i & 1u) ? 100 : 1000;
    assert(ft5955_focal_histogram_research(pixels, 5120, hist256, hist250, &m) == 0);
    assert(m.source_min == -1000 && m.source_max == -100);
    assert(m.raw_histogram[0] == 2560);
    assert(m.raw_histogram[255] == 2560);
    assert(isfinite(m.lower_mass) && isfinite(m.upper_mass));
    assert(m.lower_mass >= 0.0f && m.upper_mass >= 0.0f);
}

static void test_signed_extremes(void)
{
    int16_t pixels[FT5955_FOCAL_PIXELS];
    float hist256[256], hist250[250];
    struct ft5955_focal_hist_metrics m;
    for (size_t i = 0; i < 5120; ++i)
        pixels[i] = (i % 2u == 0u) ? INT16_MIN : INT16_MAX;
    assert(ft5955_focal_histogram_research(pixels, 5120, hist256, hist250, &m) == 0);
    assert(m.source_min == -32767 && m.source_max == 32768);
    assert(m.raw_histogram[0] == 2560 && m.raw_histogram[255] == 2560);
}

static void test_determinism_and_input_unchanged(void)
{
    int16_t pixels[FT5955_FOCAL_PIXELS];
    int16_t copy[FT5955_FOCAL_PIXELS];
    float h1[256], h2[256], t1[250], t2[250];
    struct ft5955_focal_hist_metrics m1, m2;
    for (size_t i = 0; i < 5120; ++i) pixels[i] = (int16_t)(500 + (i * 79u) % 1700u);
    memcpy(copy, pixels, sizeof copy);
    assert(ft5955_focal_histogram_research(pixels, 5120, h1, t1, &m1) == 0);
    assert(ft5955_focal_histogram_research(pixels, 5120, h2, t2, &m2) == 0);
    assert(memcmp(pixels, copy, sizeof copy) == 0);
    assert(memcmp(h1, h2, sizeof h1) == 0);
    assert(memcmp(t1, t2, sizeof t1) == 0);
    assert(memcmp(&m1, &m2, sizeof m1) == 0);
}

int main(void)
{
    test_reject_invalid();
    test_reject_flat();
    test_two_levels_and_mass();
    test_signed_extremes();
    test_determinism_and_input_unchanged();
    puts("PASS: 5 synthetic-only FocalTech histogram-pipeline tests");
    puts("Research only: no USB, fingerprints, driver installation or system changes.");
    return 0;
}
