/*
 * Isolated libfprint/NBIS diagnostic: one 8-bit grayscale image on stdin.
 * Emits ONLY the number of detected minutiae or an error; never an image,
 * template or individual minutia coordinates.
 *
 * This program links to the user's SEPARATELY BUILT libfprint, not the
 * installed system libfprint or fprintd.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gio/gio.h>
#include "fpi-image.h"

typedef struct {
  GMainLoop *loop;
  int status;
} Probe;

static void
on_detected(GObject *object, GAsyncResult *res, gpointer user_data)
{
  Probe *probe = user_data;
  FpImage *image = FP_IMAGE(object);
  GError *error = NULL;

  if (fp_image_detect_minutiae_finish(image, res, &error)) {
    GPtrArray *minutiae = fp_image_get_minutiae(image);
    printf("MINUTIAE %u\n", minutiae ? minutiae->len : 0u);
  } else if (error && g_strcmp0(error->message, "No minutiae found") == 0) {
    puts("MINUTIAE 0");
  } else {
    fprintf(stderr, "NBIS_ERROR %s\n", error ? error->message : "unknown error");
    probe->status = 3;
  }
  g_clear_error(&error);
  g_main_loop_quit(probe->loop);
}

int
main(int argc, char **argv)
{
  if (argc != 3) {
    fprintf(stderr, "Usage: ft5955_nbis_probe WIDTH HEIGHT < greyscale-8bit\n");
    return 2;
  }
  char *end_w = NULL, *end_h = NULL;
  errno = 0;
  long w = strtol(argv[1], &end_w, 10);
  long h = strtol(argv[2], &end_h, 10);
  if (errno || !end_w || *end_w || !end_h || *end_h ||
      w < 32 || h < 32 || (unsigned long)w * (unsigned long)h > 2000000UL) {
    fputs("Invalid image size\n", stderr);
    return 2;
  }
  size_t length = (size_t)w * (size_t)h;
  guint8 *pixels = g_malloc(length);
  if (fread(pixels, 1, length, stdin) != length || fgetc(stdin) != EOF) {
    fputs("Input must contain exactly width*height greyscale bytes\n", stderr);
    g_free(pixels);
    return 2;
  }
  FpImage *image = fp_image_new((gint)w, (gint)h);
  memcpy(image->data, pixels, length);
  /* Same nominal resolution used by libfprint for typical image devices. */
  image->ppmm = 500.0 / 25.4;
  g_free(pixels);

  Probe probe = {g_main_loop_new(NULL, FALSE), 0};
  fp_image_detect_minutiae(image, NULL, on_detected, &probe);
  g_main_loop_run(probe.loop);
  g_main_loop_unref(probe.loop);
  g_object_unref(image);
  return probe.status;
}
