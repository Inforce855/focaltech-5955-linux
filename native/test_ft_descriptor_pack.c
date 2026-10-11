#include "ft_descriptor_pack.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void test_shape_and_allzero(void)
{
    assert(sizeof(ft5955_feature_record) == 44u);
    float hist[128] = {0};
    uint32_t words[8] = {0};
    assert(ft5955_pack_descriptor_branch(hist, 128, words) == 0);
    for (size_t i = 0; i < 8; ++i) assert(words[i] == UINT32_MAX);
}

static void test_constant_histogram(void)
{
    float hist[128];
    uint32_t words[8];
    for (size_t i = 0; i < 128; ++i) hist[i] = 100.0f;
    assert(ft5955_pack_descriptor_branch(hist, 128, words) == 0);
    for (size_t i = 0; i < 4; ++i) assert(words[i] == UINT32_MAX);
    for (size_t i = 4; i < 8; ++i) assert(words[i] == 0);
}

static void test_channels_and_neighbor_threshold(void)
{
    float hist[128];
    uint32_t words[8];
    for (size_t i = 0; i < 64; ++i) hist[i] = 100.0f;
    for (size_t i = 64; i < 128; ++i) hist[i] = 0.0f;
    assert(ft5955_pack_descriptor_branch(hist, 128, words) == 0);
    for (size_t i = 0; i < 4; ++i) assert(words[i] == UINT32_MAX);
    for (size_t i = 4; i < 8; ++i) assert(words[i] == UINT32_C(0xaaaaaaaa));
}

static void test_selective_mean_and_circular_neighbor(void)
{
    float hist[128];
    uint32_t words[8];
    for (size_t i = 0; i < 128; ++i) hist[i] = 100.0f;
    hist[0] = 120.0f; /* cell0 / orientation0 / channel0 */
    assert(ft5955_pack_descriptor_branch(hist, 128, words) == 0);
    assert((words[0] & 1u) == 1u);
    assert((words[0] & (UINT32_C(1) << 16u)) == 0u);
    assert((words[4] & 1u) == 1u); /* cell0 greater than cell7*1.05 */
    assert((words[4] & (UINT32_C(1) << 16u)) == 0u); /* cell1 not >= cell0*1.05 */
}

static void test_bad_inputs_no_write_and_immutability(void)
{
    float hist[128], original[128];
    uint32_t words[8], again[8];
    for (size_t i = 0; i < 128; ++i) hist[i] = (float)(i % 47u);
    memcpy(original, hist, sizeof hist);
    assert(ft5955_pack_descriptor_branch(hist, 128, words) == 0);
    assert(ft5955_pack_descriptor_branch(hist, 128, again) == 0);
    assert(memcmp(hist, original, sizeof hist) == 0);
    assert(memcmp(words, again, sizeof words) == 0);
    words[0] = UINT32_C(0x12345678);
    assert(ft5955_pack_descriptor_branch(NULL, 128, words) == -1);
    assert(ft5955_pack_descriptor_branch(hist, 127, words) == -1);
    assert(ft5955_pack_descriptor_branch(hist, 128, NULL) == -1);
    hist[17] = NAN;
    assert(ft5955_pack_descriptor_branch(hist, 128, words) == -1);
    hist[17] = -1.0f;
    assert(ft5955_pack_descriptor_branch(hist, 128, words) == -1);
    assert(words[0] == UINT32_C(0x12345678));
}

int main(void)
{
    test_shape_and_allzero();
    test_constant_histogram();
    test_channels_and_neighbor_threshold();
    test_selective_mean_and_circular_neighbor();
    test_bad_inputs_no_write_and_immutability();
    puts("PASS: 5 synthetic-only FocalTech descriptor bit-packing tests");
    puts("Offline descriptor branch only; no USB, biometric captures or vendor binary.");
    return 0;
}
