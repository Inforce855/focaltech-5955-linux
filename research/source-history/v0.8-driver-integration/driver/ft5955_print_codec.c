/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_print_codec.h"
#include <openssl/sha.h>
#include <stdlib.h>
#include <string.h>

static const uint8_t magic[8] = {'F','T','5','9','5','5','P','1'};
#define ALGORITHM_MOH 1
#define POLARITY_INVERTED 1
static void le16(uint8_t *b, uint16_t n) {
  b[0] = (uint8_t)n; b[1] = (uint8_t)(n >> 8);
}
static void le32(uint8_t *b, uint32_t n) {
  b[0] = (uint8_t)n; b[1] = (uint8_t)(n >> 8);
  b[2] = (uint8_t)(n >> 16); b[3] = (uint8_t)(n >> 24);
}
static uint16_t rd16(const uint8_t *b) {
  return (uint16_t)b[0] | ((uint16_t)b[1] << 8);
}
static uint32_t rd32(const uint8_t *b) {
  return (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
         ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
}
static int equals_constant_time(const uint8_t *a, const uint8_t *b, size_t n) {
  unsigned diff = 0;
  for (size_t i=0; i<n; i++) diff |= (unsigned)(a[i]^b[i]);
  return diff == 0;
}
void ft5955_free_sensitive(void *ptr, size_t count) {
  if (!ptr) return;
  volatile uint8_t *p = (volatile uint8_t *)ptr;
  while (count--) *p++ = 0;
  free(ptr);
}
void ft5955_print_template_clear(Ft5955PrintTemplate *value) {
  if (!value) return;
  ft5955_free_sensitive(value->bytes, value->length);
  memset(value, 0, sizeof(*value));
}
int ft5955_print_pack(const uint8_t *tmpl, size_t tmpl_len, uint8_t subfactor,
                      uint8_t **out, size_t *out_len) {
  if (!out || !out_len) return -1;
  *out = NULL; *out_len = 0;
  if (!tmpl || tmpl_len == 0 || tmpl_len > FT5955_PRINT_MAX_TEMPLATE) return -1;
  const size_t total = FT5955_PRINT_HEADER_BYTES + tmpl_len + FT5955_PRINT_DIGEST_BYTES;
  uint8_t *buffer = malloc(total);
  if (!buffer) return -1;
  memcpy(buffer, magic, sizeof(magic));
  buffer[8] = ALGORITHM_MOH;
  buffer[9] = POLARITY_INVERTED;
  buffer[10] = subfactor;
  buffer[11] = 0; /* reserved flags: reject nonzero on decode */
  le16(buffer+12, 0x2808);
  le16(buffer+14, 0x5955);
  le32(buffer+16, (uint32_t)tmpl_len);
  memcpy(buffer+FT5955_PRINT_HEADER_BYTES, tmpl, tmpl_len);
  SHA256(buffer, FT5955_PRINT_HEADER_BYTES + tmpl_len,
         buffer+FT5955_PRINT_HEADER_BYTES+tmpl_len);
  *out = buffer; *out_len = total;
  return 0;
}
int ft5955_print_unpack(const uint8_t *envelope, size_t envelope_len,
                        Ft5955PrintTemplate *result) {
  if (!result) return -1;
  memset(result, 0, sizeof(*result));
  if (!envelope || envelope_len < FT5955_PRINT_HEADER_BYTES + 1 + FT5955_PRINT_DIGEST_BYTES)
    return -1;
  if (memcmp(envelope, magic, sizeof(magic)) ||
      envelope[8] != ALGORITHM_MOH || envelope[9] != POLARITY_INVERTED ||
      envelope[11] != 0 || rd16(envelope+12) != 0x2808 ||
      rd16(envelope+14) != 0x5955) return -1;
  uint32_t length = rd32(envelope+16);
  if (length == 0 || length > FT5955_PRINT_MAX_TEMPLATE ||
      envelope_len != FT5955_PRINT_HEADER_BYTES + (size_t)length + FT5955_PRINT_DIGEST_BYTES)
    return -1;
  uint8_t digest[SHA256_DIGEST_LENGTH];
  SHA256(envelope, FT5955_PRINT_HEADER_BYTES + length, digest);
  int valid = equals_constant_time(digest, envelope+FT5955_PRINT_HEADER_BYTES+length,
                                    FT5955_PRINT_DIGEST_BYTES);
  volatile uint8_t *p = digest;
  for (size_t i=0; i<sizeof(digest); i++) p[i] = 0;
  if (!valid) return -1;
  uint8_t *copy = malloc(length);
  if (!copy) return -1;
  memcpy(copy, envelope+FT5955_PRINT_HEADER_BYTES, length);
  result->bytes=copy; result->length=length; result->subfactor=envelope[10];
  return 0;
}
