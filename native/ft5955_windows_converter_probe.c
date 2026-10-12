/* Local-only private raw-image conversion / optional PGM preview.
 * The converter is reconstructed research code, NOT Windows-validated.
 * Usage: ./ft5955_windows_converter_probe local-data/capture.raw
 *        ./ft5955_windows_converter_probe local-data/capture.raw local-data/preview.pgm
 * Biometric data never goes to stdout. Created preview is owner-only 0600,
 * must be stored under gitignored local-data/, no overwrite.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_windows_converter.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int read_private_raw(const char *path, uint8_t *raw)
{
    FILE *f = fopen(path, "rb");
    if (!f) { perror("open raw"); return -1; }
    const size_t n = fread(raw, 1, FT5955_RAW_BYTES, f);
    const int extra = fgetc(f);
    const int failed = ferror(f);
    fclose(f);
    if (failed || n != FT5955_RAW_BYTES || extra != EOF) {
        fprintf(stderr, "Expected exactly %zu unframed bytes in private raw file.\n",
                (size_t)FT5955_RAW_BYTES);
        return -1;
    }
    return 0;
}

static int write_private_pgm(const char *path, const uint8_t *pixels)
{
    if (strncmp(path, "local-data/", 11) != 0 || strchr(path + 11, '/') != NULL) {
        fprintf(stderr, "Private PGM must be directly inside gitignored local-data/.\n");
        return -1;
    }
    const int fd = open(path, O_CREAT | O_EXCL | O_WRONLY, S_IRUSR | S_IWUSR);
    if (fd < 0) { perror("create PGM (no overwrites)"); return -1; }
    FILE *f = fdopen(fd, "wb");
    if (!f) { close(fd); unlink(path); return -1; }
    const int header_ok = fprintf(f, "P5\n64 80\n255\n") > 0;
    const int bytes_ok = fwrite(pixels, 1, FT5955_IMAGE_BYTES, f) == FT5955_IMAGE_BYTES;
    const int close_ok = fclose(f) == 0;
    const int ok = header_ok && bytes_ok && close_ok;
    if (!ok) {
        unlink(path);
        fprintf(stderr, "Failed to save private PGM.\n");
        return -1;
    }
    puts("Private 64x80 grayscale PGM created under gitignored local-data/ (0600).");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2 || argc > 3) {
        fprintf(stderr, "Usage: %s local-data/CAPTURE.raw [local-data/PREVIEW.pgm]\n", argv[0]);
        fprintf(stderr, "No image written without explicit preview output path.\n");
        return 2;
    }
    uint8_t raw[FT5955_RAW_BYTES];
    uint8_t out[FT5955_IMAGE_BYTES];
    struct ft5955_windows_convert_stats stats;
    if (read_private_raw(argv[1], raw) != 0) return 2;
    const int result = ft5955_windows_convert(raw, sizeof raw, out, sizeof out, &stats);
    memset(raw, 0, sizeof raw);
    if (result < 0) {
        printf("Conversion refused malformed/out-of-domain input: %d\n", result);
        return 1;
    }
    printf("Experimental 5955 Windows-conversion reconstruction; NOT DLL-validated.\n");
    printf("Conversion: %s; image 64x80\n", result == 0 ? "OK" : "uniform/empty");
    printf("Shifted 16-bit min/max: %d/%d\n", stats.shifted_min, stats.shifted_max);
    if (result == 0)
        printf("Cutoff bin: %d; scaling denominator: %d; saturated pixels: %u\n",
               stats.cutoff_bin, stats.scale_denominator, stats.saturated_pixels);
    if (argc == 3) return write_private_pgm(argv[2], out) == 0 ? 0 : 1;
    puts("No fingerprint image written to disk. Add private PGM path to opt in.");
    return 0;
}
