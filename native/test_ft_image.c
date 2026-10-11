/* Synthetic-only C regression tests: no real fingerprints or USB. */
#include "ft_image.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static void set_word(uint8_t *data, size_t index, uint16_t val)
{
    data[index * 2u] = (uint8_t)(val & 255u);
    data[index * 2u + 1u] = (uint8_t)(val >> 8u);
}

static void test_reject_bad_size_and_null(void)
{
    uint8_t raw[FT5955_RAW_BYTES] = {0};
    uint8_t out[FT5955_PIXELS];
    struct ft5955_image_metrics m;
    memset(out, 0x5a, sizeof out);
    assert(ft5955_prepare_image(raw, sizeof raw - 1u, out, sizeof out, &m) == FT5955_BAD_INPUT);
    assert(out[0] == 0x5a);
    assert(ft5955_prepare_image(NULL, sizeof raw, out, sizeof out, &m) == FT5955_BAD_INPUT);
    assert(ft5955_prepare_image(raw, sizeof raw, out, sizeof out - 1u, &m) == FT5955_BAD_INPUT);
    assert(ft5955_prepare_image(raw, sizeof raw, out, sizeof out, NULL) == FT5955_BAD_INPUT);
}

static void test_flat_image_is_rejected(void)
{
    uint8_t raw[FT5955_RAW_BYTES];
    uint8_t out[FT5955_PIXELS];
    struct ft5955_image_metrics m;
    for (size_t i = 0; i < FT5955_PIXELS; ++i) set_word(raw, i, 1200);
    memset(out, 0xff, sizeof out);
    assert(ft5955_prepare_image(raw, sizeof raw, out, sizeof out, &m) == FT5955_LOW_CONTRAST);
    assert(m.bins_with_samples == 1);
    assert(m.raw_max == 1200);
    for (size_t i = 0; i < FT5955_PIXELS; ++i) assert(out[i] == 0);
}

static void test_row_order_and_polarity(void)
{
    uint8_t raw[FT5955_RAW_BYTES];
    uint8_t out[FT5955_PIXELS];
    struct ft5955_image_metrics m;
    /* Synthetic increasing levels per row; descending grayscale is expected.
     * This is NOT intended to resemble a real fingerprint image. */
    for (size_t y = 0; y < FT5955_HEIGHT; ++y)
        for (size_t x = 0; x < FT5955_WIDTH; ++x)
            set_word(raw, y * FT5955_WIDTH + x, (uint16_t)(900u + 10u * y));
    assert(ft5955_prepare_image(raw, sizeof raw, out, sizeof out, &m) == FT5955_OK);
    assert(out[0] == 255);
    assert(out[(FT5955_HEIGHT - 1u) * FT5955_WIDTH] == 0);
    for (size_t y = 0; y < FT5955_HEIGHT; ++y) {
        const uint8_t gray = out[y * FT5955_WIDTH];
        for (size_t x = 1; x < FT5955_WIDTH; ++x)
            assert(out[y * FT5955_WIDTH + x] == gray);
        if (y > 0) assert(out[y * FT5955_WIDTH] <= out[(y - 1u) * FT5955_WIDTH]);
    }
    assert(m.clipped_negative_words == 0);
    assert(m.raw_max == 1690);
}

static void test_little_endian_and_negative_clamp(void)
{
    uint8_t raw[FT5955_RAW_BYTES] = {0};
    uint8_t out[FT5955_PIXELS];
    struct ft5955_image_metrics m;
    for (size_t i = 0; i < FT5955_PIXELS; ++i)
        set_word(raw, i, (uint16_t)(800u + i % 1000u));
    /* 0xffff is signed-negative and must be clamped before contrast inversion. */
    set_word(raw, 12, 0xffffu);
    assert(ft5955_prepare_image(raw, sizeof raw, out, sizeof out, &m) == FT5955_OK);
    assert(m.clipped_negative_words == 1);
    assert(m.raw_max == 1799);
    assert(out[12] == 255);
}

static void test_determinism_no_mutation(void)
{
    uint8_t raw[FT5955_RAW_BYTES];
    uint8_t copy[FT5955_RAW_BYTES];
    uint8_t out1[FT5955_PIXELS], out2[FT5955_PIXELS];
    struct ft5955_image_metrics a, b;
    for (size_t i = 0; i < FT5955_PIXELS; ++i)
        set_word(raw, i, (uint16_t)(1000u + ((i * 41u) % 700u)));
    memcpy(copy, raw, sizeof raw);
    assert(ft5955_prepare_image(raw, sizeof raw, out1, sizeof out1, &a) == FT5955_OK);
    assert(ft5955_prepare_image(raw, sizeof raw, out2, sizeof out2, &b) == FT5955_OK);
    assert(memcmp(raw, copy, sizeof raw) == 0);
    assert(memcmp(out1, out2, sizeof out1) == 0);
    assert(memcmp(&a, &b, sizeof a) == 0);
}

int main(void)
{
    test_reject_bad_size_and_null();
    test_flat_image_is_rejected();
    test_row_order_and_polarity();
    test_little_endian_and_negative_clamp();
    test_determinism_no_mutation();
    puts("PASS: 5 synthetic-only native image-processing tests");
    puts("No fingerprint data, USB access, files written, or OS settings changed.");
    return 0;
}
