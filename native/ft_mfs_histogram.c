#include "ft_mfs_histogram.h"

#include <math.h>
#include <string.h>

#define FT5955_MFS_PI 3.14159265358979323846f
#define FT5955_MFS_TAU (2.0f * FT5955_MFS_PI)

int ft5955_mfs_gradient_field(const float *image, size_t count,
                              float *magnitudes, float *angles)
{
    if (!image || !magnitudes || !angles || count != FT5955_MFS_PIXELS ||
        image == magnitudes || image == angles || magnitudes == angles)
        return -1;
    for (size_t i = 0; i < count; ++i)
        if (!isfinite(image[i]))
            return -1;

    for (size_t i = 0; i < count; ++i) {
        magnitudes[i] = 0.0f;
        angles[i] = 0.0f;
    }
    for (size_t y = 1; y + 1 < FT5955_MFS_HEIGHT; ++y)
        for (size_t x = 1; x + 1 < FT5955_MFS_WIDTH; ++x) {
            const size_t i = y * FT5955_MFS_WIDTH + x;
            const float dx = image[i + 1u] - image[i - 1u];
            const float dy = image[i - FT5955_MFS_WIDTH] -
                             image[i + FT5955_MFS_WIDTH];
            magnitudes[i] = hypotf(dx, dy);
            angles[i] = magnitudes[i] > 0.0f ? atan2f(dy, dx) : 0.0f;
        }
    return 0;
}

int ft5955_mfs_orientation_histogram(const float *magnitudes,
                                     const float *angles, size_t count,
                                     float center_x, float center_y,
                                     float feature_angle,
                                     float *histogram, size_t hist_count)
{
    if (!magnitudes || !angles || !histogram ||
        count != FT5955_MFS_PIXELS || hist_count != FT5955_MFS_HIST_VALUES ||
        !isfinite(center_x) || !isfinite(center_y) || !isfinite(feature_angle) ||
        center_x < 0.0f || center_x >= (float)FT5955_MFS_WIDTH ||
        center_y < 0.0f || center_y >= (float)FT5955_MFS_HEIGHT)
        return -1;
    for (size_t i = 0; i < count; ++i) {
        if (!isfinite(magnitudes[i]) || magnitudes[i] < 0.0f ||
            !isfinite(angles[i]))
            return -1;
    }

    /* These two quantities are research choices. The ELF uses a rotated
     * coordinate frame, a precomputed GAUSS_WEIGHT_TAB, and trilinear votes;
     * we have NOT identified its complete scale-specific weighting law. */
    const float cos_a = cosf(feature_angle);
    const float sin_a = sinf(feature_angle);
    const float cell_width = 4.0f;
    const float sigma = 8.0f;
    const float gaussian_denom = 2.0f * sigma * sigma;
    float result[FT5955_MFS_HIST_VALUES] = {0};

    for (int dy = -15; dy <= 15; ++dy)
        for (int dx = -15; dx <= 15; ++dx) {
            const int ix = (int)lroundf(center_x) + dx;
            const int iy = (int)lroundf(center_y) + dy;
            if (ix <= 0 || iy <= 0 || ix >= (int)FT5955_MFS_WIDTH - 1 ||
                iy >= (int)FT5955_MFS_HEIGHT - 1)
                continue;
            const size_t index = (size_t)iy * FT5955_MFS_WIDTH + (size_t)ix;
            const float mag = magnitudes[index];
            if (mag == 0.0f)
                continue;

            const float rotated_x = ((float)dx * cos_a + (float)dy * sin_a);
            const float rotated_y = (-(float)dx * sin_a + (float)dy * cos_a);
            const float cell_x = rotated_x / cell_width + 3.5f;
            const float cell_y = rotated_y / cell_width + 3.5f;
            if (cell_x <= -1.0f || cell_y <= -1.0f ||
                cell_x >= 8.0f || cell_y >= 8.0f)
                continue;

            const float phase = (angles[index] - feature_angle) *
                                (8.0f / FT5955_MFS_TAU);
            float orientation = fmodf(phase, 8.0f);
            if (orientation < 0.0f)
                orientation += 8.0f;
            const int x0 = (int)floorf(cell_x);
            const int y0 = (int)floorf(cell_y);
            const int o0 = (int)floorf(orientation);
            const float fx = cell_x - (float)x0;
            const float fy = cell_y - (float)y0;
            const float fo = orientation - (float)o0;
            const float weighted = mag *
                expf(-((float)(dx * dx + dy * dy)) / gaussian_denom);
            for (int sy = 0; sy < 2; ++sy) {
                const int cy = y0 + sy;
                if (cy < 0 || cy >= 8)
                    continue;
                const float wy = sy ? fy : 1.0f - fy;
                for (int sx = 0; sx < 2; ++sx) {
                    const int cx = x0 + sx;
                    if (cx < 0 || cx >= 8)
                        continue;
                    const float wxy = wy * (sx ? fx : 1.0f - fx);
                    for (int so = 0; so < 2; ++so) {
                        const int ob = (o0 + so) & 7;
                        const float wo = so ? fo : 1.0f - fo;
                        const size_t dest = ((size_t)cy * 8u +
                                             (size_t)cx) * 8u + (size_t)ob;
                        result[dest] += weighted * wxy * wo;
                    }
                }
            }
        }
    memcpy(histogram, result, sizeof result);
    return 0;
}
