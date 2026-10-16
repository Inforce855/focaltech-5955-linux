/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef FT5955_PRINT_CODEC_H
#define FT5955_PRINT_CODEC_H

#include <stddef.h>
#include <stdint.h>

#define FT5955_PRINT_MAX_TEMPLATE (1024u * 1024u)
#define FT5955_PRINT_HEADER_BYTES 20u
#define FT5955_PRINT_DIGEST_BYTES 32u

/* V1: FT5955P1[8], algorithm[1], polarity[1], subfactor[1], flags[1],
 * USB VID[LE16], PID[LE16], template length[LE32], template, SHA-256[32].
 * SHA-256 detects errors only: it is NOT a MAC or encryption. Treat the
 * whole print as sensitive, attacker-controlled data on import.
 */
typedef struct {
  uint8_t *bytes;  /* allocated, owned by caller; wipe with free_sensitive */
  size_t length;
  uint8_t subfactor;
} Ft5955PrintTemplate;

/* Returns 0 on success and -1 on invalid input/allocation. */
int ft5955_print_pack(const uint8_t *tmpl, size_t tmpl_len, uint8_t subfactor,
                      uint8_t **out, size_t *out_len);
int ft5955_print_unpack(const uint8_t *envelope, size_t envelope_len,
                        Ft5955PrintTemplate *result);
void ft5955_free_sensitive(void *ptr, size_t count);
void ft5955_print_template_clear(Ft5955PrintTemplate *value);
#endif
