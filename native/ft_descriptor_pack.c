#include "ft_descriptor_pack.h"
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

_Static_assert(sizeof(ft5955_feature_record) == 44u, "feature record size");
_Static_assert(offsetof(ft5955_feature_record, bDescri) == 12u, "descriptor offset");

static size_t at(size_t ch, size_t cell, size_t ori)
{
    return ch * 64u + cell * 8u + ori;
}

static void setbit(uint32_t out[8], size_t bit)
{
    out[bit / 32u] |= UINT32_C(1) << (bit % 32u);
}

int ft5955_pack_descriptor_branch(const float *histogram, size_t count,
                                   uint32_t words[FT5955_DESCRIPTOR_WORDS])
{
    if (!histogram || !words || count != FT5955_DESCRIPTOR_VALUES)
        return -1;
    for (size_t i = 0; i < count; ++i) {
        if (!isfinite(histogram[i]) || histogram[i] < 0.0f)
            return -1;
    }

    uint32_t result[FT5955_DESCRIPTOR_WORDS] = {0};
    float avg[FT5955_DESCRIPTOR_CHANNELS][FT5955_DESCRIPTOR_ORIENTATIONS] = {{0}};
    for (size_t ch = 0; ch < FT5955_DESCRIPTOR_CHANNELS; ++ch)
        for (size_t ori = 0; ori < FT5955_DESCRIPTOR_ORIENTATIONS; ++ori) {
            float sum = 0.0f;
            for (size_t cell = 0; cell < FT5955_DESCRIPTOR_CELLS; ++cell)
                sum += histogram[at(ch, cell, ori)];
            avg[ch][ori] = sum * 0.125f; /* observed rodata value at 0x193740 */
        }

    for (size_t cell = 0; cell < FT5955_DESCRIPTOR_CELLS; ++cell)
        for (size_t ori = 0; ori < FT5955_DESCRIPTOR_ORIENTATIONS; ++ori)
            for (size_t ch = 0; ch < FT5955_DESCRIPTOR_CHANNELS; ++ch) {
                const size_t bit = 2u * (cell * 8u + ori) + ch;
                const float value = histogram[at(ch, cell, ori)];
                if (value >= avg[ch][ori])
                    setbit(result, bit);
                const size_t previous = (cell + 7u) % 8u;
                /* static ELF at 0x193744: 1.0499999523f */
                const float neighbor = histogram[at(ch, previous, ori)];
                if (value >= neighbor * 1.05f)
                    setbit(result, 128u + bit);
            }

    memcpy(words, result, sizeof result);
    return 0;
}
