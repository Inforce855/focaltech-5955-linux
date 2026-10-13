/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Windows x64 per-thread last-error state for the MOH engine bridge.
 * This intentionally does not modify Linux errno.
 */
#ifndef FT5955_COMPAT_ERROR_H
#define FT5955_COMPAT_ERROR_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_ERROR_MS __attribute__((ms_abi))
#else
#error FT5955 MOH bridge requires x86-64 GCC/Clang
#endif
void FT5955_ERROR_MS ft5955_SetLastError(uint32_t code);
uint32_t FT5955_ERROR_MS ft5955_GetLastError(void);
#endif
