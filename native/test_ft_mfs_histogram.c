/* Synthetic-only feature histogram tests: no image file, real fingerprint,
 * vendor binary, USB device or login API needed. */
#include "ft_mfs_histogram.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#define PI 3.14159265358979323846f

static void test_horizontal_gradient(void)
{
    float img[FT5955_MFS_PIXELS], mag[FT5955_MFS_PIXELS], ori[FT5955_MFS_PIXELS];
    for (size_t y = 0; y < 80; ++y)
        for (size_t x = 0; x < 64; ++x)
            img[y * 64 + x] = (float)x;
    assert(ft5955_mfs_gradient_field(img, 5120, mag, ori) == 0);
    assert(fabsf(mag[40 * 64 + 32] - 2.0f) < 0.0001f);
    assert(fabsf(ori[40 * 64 + 32]) < 0.0001f);
    assert(mag[0] == 0.0f && ori[0] == 0.0f);
}
static void test_vertical_gradient(void)
{
    float img[5120], mag[5120], ori[5120];
    for (size_t y = 0; y < 80; ++y)
        for (size_t x = 0; x < 64; ++x)
            img[y * 64 + x] = (float)y;
    assert(ft5955_mfs_gradient_field(img, 5120, mag, ori) == 0);
    assert(fabsf(mag[40 * 64 + 32] - 2.0f) < 0.0001f);
    assert(fabsf(ori[40 * 64 + 32] + PI * 0.5f) < 0.0001f);
}
static void test_flat_image_has_zero_histogram(void)
{
    float img[5120] = {0}, mag[5120], ori[5120], bins[512];
    assert(ft5955_mfs_gradient_field(img, 5120, mag, ori) == 0);
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5120, 32, 40, 0, bins, 512) == 0);
    for (size_t i = 0; i < 512; ++i) assert(bins[i] == 0.0f);
}
static void test_directional_bins_and_rotation(void)
{
    float mag[5120], ori[5120], a[512], b[512];
    for (size_t i = 0; i < 5120; ++i) { mag[i] = 1.0f; ori[i] = 0.0f; }
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5120, 32, 40, 0, a, 512) == 0);
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5120, 32, 40, PI * 0.5f, b, 512) == 0);
    float sum0=0, sum6=0, off=0;
    for (size_t c = 0; c < 64; ++c) {
        sum0 += a[c * 8];
        sum6 += b[c * 8 + 6];
        for (size_t o = 1; o < 8; ++o) off += a[c * 8 + o];
    }
    assert(sum0 > 0.0f && sum6 > 0.0f && off < 0.001f);
    assert(fabsf(sum0-sum6) < 0.01f);
}
static void test_spatial_localisation_and_bounds(void)
{
    float mag[5120] = {0}, ori[5120] = {0}, bins[512];
    mag[40 * 64 + 40] = 10.0f; /* eight pixels right of central keypoint */
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5120, 32, 40, 0, bins, 512) == 0);
    float left=0, right=0;
    for (size_t y = 0; y < 8; ++y)
        for (size_t x = 0; x < 8; ++x)
            for (size_t o = 0; o < 8; ++o)
                if (x <= 3) left += bins[(y*8+x)*8+o];
                else right += bins[(y*8+x)*8+o];
    assert(right > 0.0f && left == 0.0f);
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5120, 1, 1, 0, bins, 512) == 0);
    for (size_t i = 0; i < 512; ++i) assert(isfinite(bins[i]) && bins[i] >= 0.0f);
}
static void test_error_handling_no_writes(void)
{
    float mag[5120] = {0}, ori[5120] = {0}, bins[512] = {0};
    float img[5120] = {0};
    bins[0]=314.0f;
    assert(ft5955_mfs_orientation_histogram(NULL, ori, 5120, 32, 40, 0, bins, 512) == -1);
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5119, 32, 40, 0, bins, 512) == -1);
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5120, 32, 40, 0, bins, 511) == -1);
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5120, NAN, 40, 0, bins, 512) == -1);
    mag[13]=NAN;
    assert(ft5955_mfs_orientation_histogram(mag, ori, 5120, 32, 40, 0, bins, 512) == -1);
    assert(bins[0]==314.0f);
    img[7]=INFINITY;
    assert(ft5955_mfs_gradient_field(img, 5120, mag, ori) == -1);
    assert(ft5955_mfs_gradient_field(NULL, 5120, mag, ori) == -1);
}
int main(void)
{
    test_horizontal_gradient();
    test_vertical_gradient();
    test_flat_image_has_zero_histogram();
    test_directional_bins_and_rotation();
    test_spatial_localisation_and_bounds();
    test_error_handling_no_writes();
    puts("PASS: 6 synthetic-only MFS gradient/orientation histogram tests");
    puts("Independent research approximation; no USB, biometrics or vendor binaries.");
    return 0;
}
