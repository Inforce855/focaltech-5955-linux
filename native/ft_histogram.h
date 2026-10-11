/* Synthetic-only histogram smoothing research. No USB, biometric I/O, or vendor library. */
#ifndef FT5955_HISTOGRAM_H
#define FT5955_HISTOGRAM_H

#include <stddef.h>
#include <stdint.h>

#define FT5955_HIST_BINS 256u

/* Average each bin over a centred radius-two window, clipped at the edges.
 * This five-bin filter and its repeated applications are supported by the
 * disassembly of the native FocalTech fw9362_smooth_hist32f routine.
 *
 * bins: 1..256; passes: 0..3; input/output must not overlap.
 * 0 = success, -1 = invalid arguments. The procedure does not modify input.
 * This does NOT implement the full proprietary tone-mapping algorithm.
 */
int ft5955_smooth_histogram(const uint32_t *input, float *output,
                            size_t bins, unsigned passes);

#endif
