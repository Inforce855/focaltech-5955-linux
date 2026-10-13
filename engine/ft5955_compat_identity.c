/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Correct the FT9201 loader's fixed process ID (1234) and fixed thread
 * ID (5678). Linux TIDs are unique among live threads and stable until
 * thread exit. These values are also mirrored into TEB.ClientId.
 */
#define _GNU_SOURCE
#include "ft5955_compat_identity.h"
#include <stdint.h>
#include <unistd.h>
#include <sys/syscall.h>

uint32_t FT5955_ID_MS ft5955_GetCurrentProcessId(void)
{
    const pid_t pid = getpid();
    return pid > 0 ? (uint32_t)pid : 0;
}

uint32_t FT5955_ID_MS ft5955_GetCurrentThreadId(void)
{
    const long tid = syscall(SYS_gettid);
    return tid > 0 && (uint64_t)tid <= UINT32_MAX ? (uint32_t)tid : 0;
}
