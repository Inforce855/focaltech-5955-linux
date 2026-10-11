/* Native, offline research model of one FT9362 MFS histogram-building stage.
 * NOT a byte-exact vendor implementation, nor a fingerprint authenticator.
 * No USB, files, personal biometrics, or vendor binary at runtime.
 */
#ifndef FT5955_MFS_HISTOGRAM_H
#define FT5955_MFS_HISTOGRAM_H
#include <stddef.h>

#define FT5955_MFS_WIDTH 64u
#define FT5955_MFS_HEIGHT 80u
#define FT5955_MFS_PIXELS (FT5955_MFS_WIDTH * FT5955_MFS_HEIGHT)
#define FT5955_MFS_CELLS 8u
#define FT5955_MFS_ANGLES 8u
#define FT5955_MFS_HIST_VALUES (FT5955_MFS_CELLS * FT5955_MFS_CELLS * FT5955_MFS_ANGLES)

/* Independent centre-difference approximation, not verified vendor gradient
 * quality/filter mode. Pixel and result buffers must be distinct. Interior
 * derivatives: dx=right-left, dy=above-below; outer pixels set to zero.
 * 0 success, -1 invalid input (no outputs are written on error). */
int ft5955_mfs_gradient_field(const float *image, size_t count,
                              float *magnitudes, float *angles);

/* Independent trilinear orientation histogram approximation. Consumes a
 * precomputed image-sized gradient field, not a real fingerprint template.
 * Uses a 31x31 square around keypoint and eight by eight spatial cells,
 * each with eight circular orientation bins. Magnitude-weighted Gaussian
 * votes are interpolated in x, y, and orientation. Unlike vendor code,
 * the Gaussian weights are computed, not looked up; scale and feature-mode
 * gating remain unknown. Output has 512 float entries indexed
 * ((cell_y*8+cell_x)*8+orientation_bin). No buffer mutation on invalid input.
 * 0 success, -1 invalid input or non-finite gradient data. */
int ft5955_mfs_orientation_histogram(const float *magnitudes,
                                     const float *angles, size_t count,
                                     float center_x, float center_y,
                                     float feature_angle,
                                     float *histogram, size_t hist_count);
#endif
