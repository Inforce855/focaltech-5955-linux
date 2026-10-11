/* Experimental FT9362 histogram cutoff selection, research-only.
 * No sensor access, vendor binaries, authentication, biometric input or I/O.
 */
#ifndef FT5955_FOCAL_CUTOFF_H
#define FT5955_FOCAL_CUTOFF_H
#include <stddef.h>

#define FT5955_CUTOFF_BINS 250u

struct ft5955_cutoff_result {
    size_t cutoff_bin;           /* 50..250; 250 if no suitable cutoff found */
    size_t detected_bin;         /* 0..249 when found, 250 for fallback */
    unsigned high_tail_branch;   /* 1 when upper_mass > 0.8 * lower_mass */
    float lower_mass;            /* sum bins 0..199 */
    float upper_mass;            /* sum bins 200..249 */
    float window_threshold;      /* 75 or 100*lower_mass/upper_mass */
};

/* Independently written model of the window search found by static
 * disassembly of related FT9362 code. Histogram MUST be a previously
 * smoothed, nonnegative 250-bin floating-point distribution.
 * Does not mutate input. 0 on success; -1 for invalid arguments.
 * The vendor algorithm's exact floating-point edge behavior is not validated.
 * This is not an authentication or fingerprint-matching algorithm.
 */
int ft5955_select_cutoff_bin(const float *bins, size_t count,
                             struct ft5955_cutoff_result *result);
#endif
