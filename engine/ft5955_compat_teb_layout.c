/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Isolated layout scaffolding derived from actual MOH GS/TEB disassembly.
 * IMPORTANT: synthetic PEB fields are deliberately limited, NOT a Windows
 * process. Does not set GS or allow DLL execution. Direct field access to
 * other offsets remains unverified.
 */
#define _GNU_SOURCE
#include "ft5955_compat_teb_layout.h"
#include <limits.h>
#include <pthread.h>
#include <stdint.h>
#include <string.h>

/* Windows x64 ABI offsets observed in original 5955 MOH image:
 * TEB+0x08 StackBase; TEB+0x10 StackLimit; TEB+0x30 Self;
 * TEB+0x58 ThreadLocalStoragePointer; TEB+0x60 ProcessEnvironmentBlock.
 * PEB+0x20 ProcessParameters; PEB+0xbc NtGlobalFlag;
 * RTL_USER_PROCESS_PARAMETERS+0x08 Flags.
 */
static struct {
    uint8_t peb[FT5955_PEB_BYTES];
    uint8_t params[FT5955_PROCESS_PARAMETERS_BYTES];
} process_view;
static pthread_once_t process_once = PTHREAD_ONCE_INIT;

static _Thread_local struct {
    uint8_t teb[FT5955_TEB_BYTES];
    void *crt_slots[FT5955_CRT_TLS_SLOTS];
    uint8_t crt_template[FT5955_CRT_TLS_BYTES];
    int prepared;
} current;

static void store_ptr(uint8_t *base, size_t offset, const void *value)
{
    uintptr_t address = (uintptr_t)value;
    memcpy(base + offset, &address, sizeof address);
}
static void store_u32(uint8_t *base, size_t offset, uint32_t value)
{
    memcpy(base + offset, &value, sizeof value);
}
static void prepare_process(void)
{
    /* These flags are synthetic and must be validated against engine use.
     * Zero NtGlobalFlag means no debugger heap diagnostics enabled.
     * Flags=1 denotes normalized RTL_USER_PROCESS_PARAMETERS pointers.
     */
    store_ptr(process_view.peb, 0x20, process_view.params);
    store_u32(process_view.peb, 0xbc, 0);
    store_u32(process_view.params, 0x08, 1);
}
int ft5955_teb_prepare_current(void)
{
    /* Re-entering the engine on the same pthread must preserve CRT TLS data. */
    if (current.prepared)
        return 0;
    pthread_attr_t attr;
    void *stack_low = NULL;
    size_t stack_size = 0;
    volatile uint8_t on_stack = 0;

    if (pthread_getattr_np(pthread_self(), &attr) != 0)
        return -1;
    int status = pthread_attr_getstack(&attr, &stack_low, &stack_size);
    pthread_attr_destroy(&attr);
    if (status != 0 || !stack_low || !stack_size)
        return -2;
    uintptr_t low = (uintptr_t)stack_low;
    if (stack_size > UINTPTR_MAX - low)
        return -3;
    uintptr_t high = low + stack_size;
    uintptr_t marker = (uintptr_t)&on_stack;
    if (marker <= low || marker >= high)
        return -4;

    if (pthread_once(&process_once, prepare_process) != 0)
        return -5;
    /* Entire TEB and TLS area must be private to the current pthread. */
    memset(current.teb, 0, sizeof current.teb);
    memset(current.crt_slots, 0, sizeof current.crt_slots);
    memset(current.crt_template, 0, sizeof current.crt_template);
    current.crt_slots[0] = current.crt_template;
    store_ptr(current.teb, 0x08, (void *)high);
    store_ptr(current.teb, 0x10, (void *)low);
    store_ptr(current.teb, 0x30, current.teb);
    store_ptr(current.teb, 0x58, current.crt_slots);
    store_ptr(current.teb, 0x60, process_view.peb);
    current.prepared = 1;
    return 0;
}
const uint8_t *ft5955_teb_view_current(void)
{
    return current.prepared ? current.teb : NULL;
}
const uint8_t *ft5955_peb_view(void)
{
    if (pthread_once(&process_once, prepare_process) != 0)
        return NULL;
    return process_view.peb;
}
const uint8_t *ft5955_process_parameters_view(void)
{
    if (pthread_once(&process_once, prepare_process) != 0)
        return NULL;
    return process_view.params;
}
int ft5955_teb_set_crt_tls_template(const uint8_t *data, size_t length)
{
    if (!current.prepared || length > sizeof current.crt_template ||
        (!data && length))
        return -1;
    memset(current.crt_template, 0, sizeof current.crt_template);
    if (length)
        memcpy(current.crt_template, data, length);
    return 0;
}
