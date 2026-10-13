/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Bounded in-process Windows environment for the gated MOH experiment.
 * Does not read or modify host environ, setenv(), or the Linux filesystem.
 */
#ifndef FT5955_COMPAT_ENV_H
#define FT5955_COMPAT_ENV_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_ENV_MS __attribute__((ms_abi))
#else
#error Experimental MOH bridge requires x86-64 GCC or Clang
#endif
int FT5955_ENV_MS ft5955_SetEnvironmentVariableW(const uint16_t *name,
                                                  const uint16_t *value);
uint16_t *FT5955_ENV_MS ft5955_GetEnvironmentStringsW(void);
int FT5955_ENV_MS ft5955_FreeEnvironmentStringsW(uint16_t *block);
#endif
