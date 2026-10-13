/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Inert Windows x64 TEB/PEB layout fixture for 5955 MOH compatibility.
 * Does NOT set GS, load a PE, or invoke any Windows code.
 */
#ifndef FT5955_COMPAT_TEB_LAYOUT_H
#define FT5955_COMPAT_TEB_LAYOUT_H
#include <stddef.h>
#include <stdint.h>

enum {
    FT5955_TEB_BYTES = 0x2000,
    FT5955_PEB_BYTES = 0x1000,
    FT5955_PROCESS_PARAMETERS_BYTES = 0x1000,
    FT5955_CRT_TLS_SLOTS = 64,
    FT5955_CRT_TLS_BYTES = 0x2000
};

/* Pointers remain valid for the lifetime of the calling pthread.
 * Stack bounds are those reported by pthread_getattr_np for this thread.
 * Thread-local TEB pointers must NEVER be used by a different thread.
 */
int ft5955_teb_prepare_current(void);
const uint8_t *ft5955_teb_view_current(void);
const uint8_t *ft5955_peb_view(void);
const uint8_t *ft5955_process_parameters_view(void);
/* Synthetic CRT TLS template, max FT5955_CRT_TLS_BYTES, copied per thread. */
int ft5955_teb_set_crt_tls_template(const uint8_t *data, size_t length);

#endif
