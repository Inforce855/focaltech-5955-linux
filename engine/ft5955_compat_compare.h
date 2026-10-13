/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Limited CompareStringW ABI for the experimental 5955 WinBio engine.
 */
#ifndef FT5955_COMPAT_COMPARE_H
#define FT5955_COMPAT_COMPARE_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_COMPARE_MS __attribute__((ms_abi))
#else
#error The FocalTech MOH loader currently requires x86-64 GCC or Clang
#endif
#define FT5955_NORM_IGNORECASE 0x00000001u
#define FT5955_CSTR_LESS_THAN 1
#define FT5955_CSTR_EQUAL 2
#define FT5955_CSTR_GREATER_THAN 3
int FT5955_COMPARE_MS ft5955_CompareStringW(uint32_t lcid, uint32_t flags,
    const uint16_t *a, int length_a, const uint16_t *b, int length_b);
#endif
