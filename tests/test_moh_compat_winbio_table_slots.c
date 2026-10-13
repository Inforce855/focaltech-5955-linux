/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic proof that callback slots do not overwrite WinBio headers.
 * Does not load DLL or access USB.
 */
#include "ft5955_winbio_interface_probe.h"
#include "ft5955_compat_callbacks.h"
#include <stdint.h>
#include <stdio.h>
int main(void)
{
    ft5955_winbio_interface_probe storage;
    ft5955_winbio_interface_probe_init(&storage,FT5955_WINBIO_STORAGE_TYPE);
    for(size_t i=0;i<FT5955_WINBIO_PROBE_SLOTS;i++)
        storage.slots[i]=(uint64_t)(uintptr_t)ft5955_unimplemented_callback;
    storage.slots[(0x68u-0x20u)/8u]=UINT64_C(0x12345678);
    if(storage.size!=0x100u || storage.version_major!=3 ||
       storage.type!=FT5955_WINBIO_STORAGE_TYPE ||
       storage.slots[9]!=UINT64_C(0x12345678) ||
       storage.slots[0]!=(uint64_t)(uintptr_t)ft5955_unimplemented_callback){
        fputs("5955 WinBio header/callback separation FAILED\n",stderr);return 1;
    }
    puts("5955 WinBio header/callback separation: synthetic test OK");
    return 0;
}
