#include "ft_focal_cutoff.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static void test_invalid(void)
{
    float bins[FT5955_CUTOFF_BINS] = {0};
    struct ft5955_cutoff_result result;
    assert(ft5955_select_cutoff_bin(NULL, 250, &result) == -1);
    assert(ft5955_select_cutoff_bin(bins, 249, &result) == -1);
    assert(ft5955_select_cutoff_bin(bins, 250, NULL) == -1);
    bins[12] = NAN;
    assert(ft5955_select_cutoff_bin(bins, 250, &result) == -1);
    bins[12] = -1.0f;
    assert(ft5955_select_cutoff_bin(bins, 250, &result) == -1);
}

static void test_empty_fallback(void)
{
    float bins[FT5955_CUTOFF_BINS] = {0};
    struct ft5955_cutoff_result result;
    assert(ft5955_select_cutoff_bin(bins, 250, &result) == 0);
    assert(result.cutoff_bin == 250u);
    assert(result.detected_bin == 250u);
    assert(result.high_tail_branch == 0u);
    assert(result.window_threshold == 75.0f);
}

static void test_normal_window_and_plus_thirty(void)
{
    float bins[FT5955_CUTOFF_BINS] = {0};
    struct ft5955_cutoff_result result;
    bins[100] = 1000.0f;
    assert(ft5955_select_cutoff_bin(bins, 250, &result) == 0);
    assert(result.high_tail_branch == 0u);
    assert(result.detected_bin == 102u);
    assert(result.cutoff_bin == 132u);
}

static void test_upper_tail_specific_window(void)
{
    float bins[FT5955_CUTOFF_BINS] = {0};
    struct ft5955_cutoff_result result;
    bins[220] = 1000.0f;
    bins[150] = 500.0f;
    bins[10] = 100.0f;
    assert(ft5955_select_cutoff_bin(bins, 250, &result) == 0);
    assert(result.high_tail_branch == 1u);
    assert(result.window_threshold == 60.0f);
    assert(result.detected_bin == 152u);
    assert(result.cutoff_bin == 152u);
}

static void test_no_six_bin_gap_and_immutable(void)
{
    float bins[FT5955_CUTOFF_BINS] = {0};
    float copy[FT5955_CUTOFF_BINS];
    struct ft5955_cutoff_result a, b;
    for (int i = 240; i > 40; i -= 8)
        bins[i] = 1000.0f;
    memcpy(copy, bins, sizeof bins);
    assert(ft5955_select_cutoff_bin(bins, 250, &a) == 0);
    assert(ft5955_select_cutoff_bin(bins, 250, &b) == 0);
    assert(a.cutoff_bin == 250u);
    assert(memcmp(copy, bins, sizeof bins) == 0);
    assert(memcmp(&a, &b, sizeof a) == 0);
}

int main(void)
{
    test_invalid();
    test_empty_fallback();
    test_normal_window_and_plus_thirty();
    test_upper_tail_specific_window();
    test_no_six_bin_gap_and_immutable();
    puts("PASS: 5 synthetic-only FocalTech histogram cutoff-selection tests");
    puts("No USB, biometric data, vendor execution or system changes.");
    return 0;
}
