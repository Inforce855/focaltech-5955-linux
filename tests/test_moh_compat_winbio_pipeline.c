/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Inert WinBio pipeline layout contract. No DLL, no USB, no fingerprints.
 */
#include "ft5955_winbio_pipeline.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    ft5955_winbio_pipeline p;
    memset(&p,0,sizeof p);
    p.engine_handle=(void*)(uintptr_t)UINT64_MAX;
    if((uintptr_t)p.engine_handle!=UINT64_MAX || p.engine_context!=NULL ||
       sizeof p!=0x50 || (unsigned char *)&p.engine_context-(unsigned char *)&p!=0x38 ||
       (unsigned char *)&p.storage_interface-(unsigned char *)&p!=0x28) {
        fputs("5955 WinBio pipeline ABI test FAILED\n",stderr);
        return 1;
    }
    puts("5955 documented WINBIO_PIPELINE x64 layout: synthetic tests OK");
    return 0;
}
