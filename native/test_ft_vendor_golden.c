/* Synthetic-output golden vectors from original FocalTech FT9362 Linux ELF.
 * Vendor normalizer was run separately in an isolated offline namespace.
 * This test uses ONLY our native C: no vendor library, USB, biometrics or PAM.
 * Output parity for eight synthetic images does not prove the 5955 sensor's
 * calibration, Windows DLL equivalence, or authentication reliability.
 */
#include "ft_focal_tone_v3.h"
#include "ft_focal_histogram.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct golden {
    const char *name;
    uint64_t sum;
    uint64_t fnv;
    size_t cutoff;
    unsigned tail;
};

static const struct golden cases[] = {
    {"ramp",         UINT64_C(650235),  UINT64_C(0xf70d36fc204f78e8), 250u, 0u},
    {"concentrated", UINT64_C(921495),  UINT64_C(0xce75df5f8171f30a), 141u, 0u},
    {"twolevel",     UINT64_C(650240),  UINT64_C(0x26ca0b5e8b63f325), 250u, 0u},
    {"tail",         UINT64_C(875927),  UINT64_C(0xc72568cad7d0d812), 250u, 1u},
    {"random",       UINT64_C(648851),  UINT64_C(0x891cabdef20108fa), 250u, 0u},
    {"column",       UINT64_C(650232),  UINT64_C(0x3880220096263139), 250u, 0u},
    {"nearflat",     UINT64_C(650970),  UINT64_C(0xfc9ff5b4d86b532f), 250u, 0u},
    {"tailadjust",   UINT64_C(1003000), UINT64_C(0x6f5026e6b88368ed), 147u, 1u},
};

static void synthetic_input(const char *mode, int16_t *p)
{
    for (size_t i = 0; i < FT5955_FOCAL_PIXELS; ++i) {
        if (strcmp(mode, "ramp") == 0)
            p[i] = (int16_t)(i % 1024u);
        else if (strcmp(mode, "concentrated") == 0)
            p[i] = 600;
        else if (strcmp(mode, "twolevel") == 0)
            p[i] = (i % 2u) ? 100 : 1000;
        else if (strcmp(mode, "tail") == 0)
            p[i] = (i < 4000u) ? 140 : 1000;
        else if (strcmp(mode, "random") == 0)
            p[i] = (int16_t)(400u +
                (((uint32_t)i * UINT32_C(1103515245) +
                   UINT32_C(12345)) % 1400u));
        else if (strcmp(mode, "column") == 0)
            p[i] = (int16_t)(400u + (i % 64u) * 23u + (i / 64u) * 4u);
        else if (strcmp(mode, "nearflat") == 0)
            p[i] = (int16_t)(1200u + i % 23u);
        else if (strcmp(mode, "tailadjust") == 0)
            p[i] = (i < 3000u) ? 140 : ((i < 4000u) ? 450 : 1000);
    }
    if (strcmp(mode, "concentrated") == 0) {
        p[0] = 0; p[1] = 1000;
    } else if (strcmp(mode, "tail") == 0) {
        p[3] = 0; p[1] = 200; p[2] = 500;
    } else if (strcmp(mode, "tailadjust") == 0) {
        p[0] = 0;
    }
}

int main(void)
{
    size_t passed = 0;
    for (size_t c = 0; c < sizeof cases / sizeof cases[0]; ++c) {
        int16_t input[FT5955_FOCAL_PIXELS], copy[FT5955_FOCAL_PIXELS];
        uint8_t output[FT5955_FOCAL_PIXELS];
        struct ft5955_tone_v3_metrics metrics;
        synthetic_input(cases[c].name, input);
        memcpy(copy, input, sizeof input);
        const int status = ft5955_tone_v3_normalize(input,
            FT5955_FOCAL_PIXELS, output, sizeof output, &metrics);
        if (status != 0 || memcmp(copy, input, sizeof input) != 0) {
            fprintf(stderr, "FAIL: %s status=%d or input mutated\n",
                    cases[c].name, status);
            return 1;
        }
        uint64_t sum = 0, fnv = UINT64_C(14695981039346656037);
        for (size_t i = 0; i < sizeof output; ++i) {
            sum += output[i];
            fnv = (fnv ^ output[i]) * UINT64_C(1099511628211);
        }
        if (sum != cases[c].sum || fnv != cases[c].fnv ||
            metrics.cutoff.cutoff_bin != cases[c].cutoff ||
            metrics.cutoff.high_tail_branch != cases[c].tail) {
            fprintf(stderr, "FAIL: %s sum=%" PRIu64 " fnv=%016" PRIx64
                            " cutoff=%zu tail=%u\n",
                    cases[c].name, sum, fnv, metrics.cutoff.cutoff_bin,
                    metrics.cutoff.high_tail_branch);
            return 1;
        }
        ++passed;
    }
    printf("PASS: %zu synthetic-only vendor-output golden vectors (native C)\n", passed);
    puts("No vendor binary, USB, biometric data or authentication code executed.");
    return 0;
}
