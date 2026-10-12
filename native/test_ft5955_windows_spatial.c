/* Synthetic-only tests for the independent 5955 Windows spatial stage.
 * No sensor access, Windows DLL, fingerprints or stored biometric data. */
#include "ft5955_windows_spatial.h"
#include <assert.h>
#include <stdio.h>

#define W FT5955_SPATIAL_WIDTH
#define AT(y, x) image[(y) * W + (x)]
static uint16_t image[FT5955_SPATIAL_SAMPLES];

static void
fill(uint16_t value)
{
    for (size_t i = 0; i < FT5955_SPATIAL_SAMPLES; ++i)
        image[i] = value;
}

int
main(void)
{
    assert(ft5955_windows_spatial_correct(NULL, FT5955_SPATIAL_SAMPLES) == -1);
    assert(ft5955_windows_spatial_correct(image, FT5955_SPATIAL_SAMPLES - 1) == -1);

    fill(100);
    AT(5, 5) = (uint16_t)-1; /* negative raw sample clamped to zero */
    assert(ft5955_windows_spatial_correct(image, FT5955_SPATIAL_SAMPLES) == 0);
    assert(AT(5, 5) == 100); /* zero impulse replaced by four neighbours */

    fill(100);
    AT(5, 5) = 400;
    assert(ft5955_windows_spatial_correct(image, FT5955_SPATIAL_SAMPLES) == 0);
    assert(AT(5, 5) == 100); /* bright impulse */

    fill(100);
    AT(5, 5) = 149;
    assert(ft5955_windows_spatial_correct(image, FT5955_SPATIAL_SAMPLES) == 0);
    assert(AT(5, 5) == 149); /* difference <=50 is preserved */

    fill(100);
    AT(20, 10) = 400;
    AT(21, 10) = 400;
    assert(ft5955_windows_spatial_correct(image, FT5955_SPATIAL_SAMPLES) == 0);
    assert(AT(20, 10) == 175); /* three low neighbours -> (300+400)/4 */

    fill(100);
    AT(20, 10) = 400;
    AT(20, 11) = 400;
    AT(21, 10) = 400;
    assert(ft5955_windows_spatial_correct(image, FT5955_SPATIAL_SAMPLES) == 0);
    assert(AT(20, 10) == 400); /* only two low neighbours */

    fill(100);
    AT(10, 0) = 10;
    AT(10, 1) = 20;
    AT(10, 2) = 200;
    AT(10, 61) = 205;
    AT(10, 62) = 30;
    AT(10, 63) = 40;
    assert(ft5955_windows_spatial_correct(image, FT5955_SPATIAL_SAMPLES) == 0);
    assert(AT(10, 0) == 200 && AT(10, 1) == 200);
    assert(AT(10, 62) == 205 && AT(10, 63) == 205);

    fill(100);
    AT(0, 15) = 300;
    AT(1, 15) = 123;
    AT(78, 15) = 234;
    AT(79, 15) = 400;
    assert(ft5955_windows_spatial_correct(image, FT5955_SPATIAL_SAMPLES) == 0);
    assert(AT(0, 15) == 123 && AT(79, 15) == 234);

    puts("spatial correction synthetic tests: OK");
    return 0;
}
