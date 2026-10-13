/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Evidence-backed partial pipeline layout for the 5955 MOH Attach function.
 * NOT a complete WINBIO_PIPELINE definition and NOT enabled for Attach.
 * Derived from SHA-pinned MOH engine Attach RVA 0x128d20.
 */
#ifndef FT5955_PIPELINE_PROBE_H
#define FT5955_PIPELINE_PROBE_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef struct {
    uint8_t unknown_00[0x08];
    uint64_t invalid_handle_sentinel; /* +0x08: Attach checks all bits set */
    uint8_t unknown_10[0x28];
    void *engine_context;             /* +0x38: must be NULL on Attach */
    uint8_t unknown_40[0x3c0];        /* 1024-byte legacy buffer boundary */
} ft5955_pipeline_probe;
_Static_assert(offsetof(ft5955_pipeline_probe,invalid_handle_sentinel)==0x08,
               "5955 pipeline sentinel offset");
_Static_assert(offsetof(ft5955_pipeline_probe,engine_context)==0x38,
               "5955 pipeline engine context offset");
_Static_assert(sizeof(ft5955_pipeline_probe)==1024,"5955 pipeline buffer size");
#define FT5955_ENGINE_CONTEXT_MAGIC UINT32_C(0x28069900)
#define FT5955_ENGINE_CONTEXT_MAGIC_OFFSET 0x18u
static inline void ft5955_pipeline_probe_init(ft5955_pipeline_probe *pipeline)
{
    memset(pipeline,0,sizeof(*pipeline));
    pipeline->invalid_handle_sentinel=UINT64_MAX;
}
#endif
