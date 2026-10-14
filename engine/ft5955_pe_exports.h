/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Checked PE32+ export lookup over an inert, prepared image buffer.
 * No PE loading, execution, dynamic linkage or system modification.
 */
#ifndef FT5955_PE_EXPORTS_H
#define FT5955_PE_EXPORTS_H
#include <stddef.h>
#include <stdint.h>
/* Return 0 with a bounded function RVA; -1 on absent/invalid/forwarded
 * export. Caller must independently check executable section permissions.
 */
int ft5955_pe_find_export(const uint8_t *image, size_t image_size,
                          uint32_t directory_rva, uint32_t directory_size,
                          const char *name, uint32_t *function_rva);
#endif
