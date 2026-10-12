/* Synthetic tests only: no real fingerprint samples or USB communication. */
#include "ft5955_windows_converter.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static uint8_t raw[FT5955_RAW_BYTES];
static uint8_t result[FT5955_IMAGE_BYTES];
static struct ft5955_windows_convert_stats stats;

static void set_pixel(size_t i, int16_t v)
{
    raw[2*i] = (uint8_t)(uint16_t)v;
    raw[2*i+1] = (uint8_t)((uint16_t)v >> 8);
}
static void gradient(void)
{
    /* Vertical stripes of regular increasing intensity, including entire
     * 64-word width. Entirely synthetic, unrelated to fingerprint ridges. */
    for (size_t y=0;y<FT5955_SPATIAL_HEIGHT;y++)
        for (size_t x=0;x<FT5955_SPATIAL_WIDTH;x++)
            set_pixel(y*FT5955_SPATIAL_WIDTH+x, (int16_t)(x * 10));
}
int main(void)
{
    assert(ft5955_windows_convert(NULL, sizeof raw, result, sizeof result, &stats) == -1);
    assert(ft5955_windows_convert(raw, sizeof raw - 1, result, sizeof result, &stats) == -1);
    memset(raw, 0, sizeof raw);
    assert(ft5955_windows_convert(raw, sizeof raw, result, sizeof result, &stats) == 1);
    for (size_t i=0;i<sizeof result;i++) assert(result[i] == 0);

    gradient();
    assert(ft5955_windows_convert(raw, sizeof raw, result, sizeof result, &stats) == 0);
    assert(stats.shifted_min == 0);
    assert(stats.shifted_max == 590); /* edge repair: raw low=20, high=610 */
    assert(stats.cutoff_bin >= 50 && stats.cutoff_bin <= 250);
    assert(stats.scale_denominator > 0);
    assert(result[5] >= result[15]); /* negation reverses raw polarity */
    assert(result[0] == result[1] && result[1] == result[2]);
    assert(result[61] == result[62] && result[62] == result[63]);
    for (size_t i=0;i<sizeof result;i++) assert(result[i] <= 255);

    /* Signed negative sample is clamped to zero by spatial stage. */
    gradient();
    set_pixel(10*FT5955_SPATIAL_WIDTH+10, -135);
    assert(ft5955_windows_convert(raw, sizeof raw, result, sizeof result, &stats) == 0);

    puts("windows converter synthetic tests: OK");
    return 0;
}
