/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic Windows temp-path namespace, no host filesystem mapping.
 */
#ifndef FT5955_COMPAT_TEMP_H
#define FT5955_COMPAT_TEMP_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_TEMP_MS __attribute__((ms_abi))
#else
#error FocalTech engine requires x86-64 GCC/Clang
#endif
/* Returns number of WCHARs copied EXCLUDING NUL when space is sufficient;
 * otherwise required size INCLUDING NUL, per Win32 GetTempPathW. */
uint32_t FT5955_TEMP_MS ft5955_GetTempPathW(uint32_t length,
                                            uint16_t *buffer);
#endif
