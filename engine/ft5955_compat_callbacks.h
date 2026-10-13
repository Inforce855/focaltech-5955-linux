/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Fallback for unknown MOH WinBio callbacks. An unverified slot must fail.
 * This is NOT proof of a method's Windows x64 signature.
 */
#ifndef FT5955_COMPAT_CALLBACKS_H
#define FT5955_COMPAT_CALLBACKS_H
#include <stdint.h>
#if !defined(__x86_64__) || !defined(__GNUC__)
#error This compatibility layer requires x86-64 GCC or Clang
#endif
#define FT5955_E_NOTIMPL UINT64_C(0x80004001)
static uint64_t __attribute__((ms_abi)) ft5955_unimplemented_callback(
  void *a,void *b,void *c,void *d,void *e,void *f)
{
  (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;
  return FT5955_E_NOTIMPL;
}
#endif
