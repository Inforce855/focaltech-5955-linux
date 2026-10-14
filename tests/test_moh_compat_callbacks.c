/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic Windows x64 ABI test: no DLL, USB, or biometric material.
 */
#include "ft5955_compat_callbacks.h"
#include <stdio.h>
int main(void) {
  typedef uint64_t (__attribute__((ms_abi)) *callback)(void*,void*,void*,void*,void*,void*);
  volatile callback entry = ft5955_unimplemented_callback;
  uint64_t result=entry((void*)1,(void*)2,(void*)3,(void*)4,(void*)5,(void*)6);
  if(result!=FT5955_E_NOTIMPL) {
    fprintf(stderr,"Fail-closed callback returned 0x%llx\n",(unsigned long long)result);
    return 1;
  }
  puts("5955 default callback: E_NOTIMPL, synthetic ABI test OK");
  return 0;
}
