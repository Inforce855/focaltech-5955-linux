/* Independently written study of FocalTech ST_Feature bit-packing stage.
 * Input is SYNTHETIC float histograms, not raw fingerprint images.
 * This is only one descriptor branch. It does not locate keypoints or
 * implement enrollment, authentication, matching, or device I/O.
 */
#ifndef FT5955_DESCRIPTOR_PACK_H
#define FT5955_DESCRIPTOR_PACK_H
#include <stddef.h>
#include <stdint.h>

#define FT5955_DESCRIPTOR_CHANNELS 2u
#define FT5955_DESCRIPTOR_CELLS 8u
#define FT5955_DESCRIPTOR_ORIENTATIONS 8u
#define FT5955_DESCRIPTOR_VALUES 128u
#define FT5955_DESCRIPTOR_WORDS 8u

typedef struct {
    float x;
    float y;
    float ori;
    uint32_t bDescri[FT5955_DESCRIPTOR_WORDS];
} ft5955_feature_record;

/* Flat histogram indexing: [channel][spatial_cell][orientation_bin].
 * Output is bDescri[0..7]; LSB first in each word.
 * 0 success; -1 invalid pointer, count, or nonfinite/negative histogram.
 * Writes output only on success and never changes histogram.
 * This covers the mean-threshold plus adjacent-cell branch confirmed in
 * the 2025 Ubuntu FocalTech FT9362 ELF. Exact full extractor is unverified.
 */
int ft5955_pack_descriptor_branch(const float *histogram, size_t count,
                                   uint32_t words[FT5955_DESCRIPTOR_WORDS]);
#endif
