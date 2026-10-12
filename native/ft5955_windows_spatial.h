/* Independent reconstruction of one Windows MOH correction helper.
 * PRIVATE-DLL EVIDENCE: FtWbioDriverUmdfV3.dll,
 * SHA256 b2dd3b0a5c79c9a9bc628ccbfdbd20b83e63799d9d310ae513c378c7af1b958e,
 * image VA 0x180006184. No proprietary code is linked.
 * Does NOT perform histogram conversion, recognition or login.
 */
#ifndef FT5955_WINDOWS_SPATIAL_H
#define FT5955_WINDOWS_SPATIAL_H
#include <stddef.h>
#include <stdint.h>
#define FT5955_SPATIAL_WIDTH 64u
#define FT5955_SPATIAL_HEIGHT 80u
#define FT5955_SPATIAL_SAMPLES (FT5955_SPATIAL_WIDTH * FT5955_SPATIAL_HEIGHT)

/* Correct exactly 5120 host-order raw 16-bit sample bit patterns in place.
 * An original 16-bit signed-negative sample is converted to zero.
 * Returns 0 for success or -1 for invalid pointer/count. */
int ft5955_windows_spatial_correct(uint16_t *samples, size_t count);
#endif
