/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Each Windows thread has its own LastErrorValue in its TEB.
 * Approximate the public GetLastError/SetLastError contract using native
 * C11 TLS. Do not confuse these values with process-wide errno.
 */
#include "ft5955_compat_error.h"
static _Thread_local uint32_t win32_last_error;

void FT5955_ERROR_MS ft5955_SetLastError(uint32_t code)
{
    win32_last_error = code;
}
uint32_t FT5955_ERROR_MS ft5955_GetLastError(void)
{
    return win32_last_error;
}
