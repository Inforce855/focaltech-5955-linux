/* Experimental reconstruction of the native FocalTech histogram *stages*.
 * This works on purely in-memory signed 16-bit image arrays, not hardware.
 * No identity analysis, no live biometric input, no USB, and no vendor binaries.
 */
#ifndef FT5955_FOCAL_HISTOGRAM_H
#define FT5955_FOCAL_HISTOGRAM_H

#include <stddef.h>
#include <stdint.h>

#define FT5955_FOCAL_PIXELS 5120u
#define FT5955_FOCAL_HIST_BINS 256u
#define FT5955_FOCAL_FINAL_BINS 250u

struct ft5955_focal_hist_metrics {
    int32_t source_min;
    int32_t source_max;
    uint32_t raw_histogram[FT5955_FOCAL_HIST_BINS];
    float lower_mass;  /* smoothed histogram sum bins [0,199] */
    float upper_mass;  /* smoothed histogram sum bins [200,249] */
    int high_tail_branch; /* upper_mass > 0.8 * lower_mass; from binary */
};

/* 0=success, 1=flat frame, -1=invalid arguments. No input mutation.
 * This reconstructs intermediate histogram shape, NOT the final pixel map.
 * The library referenced here is for a RELATED FT9362 image path, not
 * a verified identical path for the 2808:5955 reader.
 */
int ft5955_focal_histogram_research(const int16_t *pixels, size_t count,
                                    float output256[FT5955_FOCAL_HIST_BINS],
                                    float output250[FT5955_FOCAL_FINAL_BINS],
                                    struct ft5955_focal_hist_metrics *metrics);
#endif
