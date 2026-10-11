/* Experimental independent, synthetic-only image tone mapping study.
 * Derived from static analysis of RELATED native FocalTech FT9362 code;
 * not validated as equivalent to the 2808:5955 vendor processing.
 * No USB, vendor binary execution, fingerprint files or authentication.
 */
#ifndef FT5955_FOCAL_TONE_H
#define FT5955_FOCAL_TONE_H

#include <stddef.h>
#include <stdint.h>
#include "ft_focal_histogram.h"

struct ft5955_focal_tone_metrics {
    int32_t negated_min;
    int32_t negated_max;
    uint32_t contrast_limit;
    uint32_t saturated_count;
    uint16_t contrast_fraction_of_250; /* 200 or 250 */
    int high_tail_branch;
};

/* Signed 16-bit input is already decoded into host-endian samples.
 * Output is 5120 bytes of experimental 8-bit grayscale.
 * Returns 0: success; 1: flat or unresolvable contrast; -1: bad args.
 * Exact-size checks, no input mutation. Do not use for auth decisions.
 */
int ft5955_focal_tone_research(const int16_t *samples, size_t count,
                               uint8_t *out, size_t out_bytes,
                               struct ft5955_focal_tone_metrics *metrics);
#endif
