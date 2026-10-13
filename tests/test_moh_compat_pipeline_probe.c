/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic, non-executing verification of the observed 5955 Attach fields.
 */
#include "ft5955_pipeline_probe.h"
#include <stdio.h>
int main(void)
{
    ft5955_pipeline_probe pipeline;
    ft5955_pipeline_probe_init(&pipeline);
    if(pipeline.invalid_handle_sentinel != UINT64_MAX ||
       pipeline.engine_context != NULL ||
       FT5955_ENGINE_CONTEXT_MAGIC != UINT32_C(0x28069900) ||
       FT5955_ENGINE_CONTEXT_MAGIC_OFFSET != 0x18u) {
        fputs("5955 partial pipeline layout test FAILED\n",stderr);
        return 1;
    }
    puts("5955 observed Attach pipeline offsets: synthetic tests OK");
    return 0;
}
