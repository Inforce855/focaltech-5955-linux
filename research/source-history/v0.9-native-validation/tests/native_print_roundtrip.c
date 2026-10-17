/* SPDX-License-Identifier: LGPL-2.1-or-later
 * FT5955 experimental private-libfprint real FpPrint roundtrip test.
 * All biometric data remains in process memory; NO files, fprintd, PAM or login.
 * User-guided same/different finger controls; the user must not switch fingers
 * during the 12 accepted-impression enrolment.
 */
#include "fprint.h"
#include <glib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define MAX_SERIALIZED (2u * 1024u * 1024u)

static void wipe(void *ptr, gsize n) {
  volatile guint8 *p = ptr;
  if (p) while (n--) *p++ = 0;
}

static gboolean ask(const char *message) {
  char input[128] = {0};
  g_print("%s", message);
  fflush(stdout);
  if (!fgets(input, sizeof input, stdin)) return FALSE;
  if (input[0] == 'q' || input[0] == 'Q') return FALSE;
  if (input[0] != '\n' && input[0] != '\r') {
    g_printerr("Only Enter begins a scan. Session cancelled.\n");
    return FALSE;
  }
  return TRUE;
}

static void on_enroll(FpDevice *device, gint accepted, FpPrint *print,
                      gpointer userdata, GError *error) {
  if (error)
    g_print("  Scan rejected (still %d/12); lift finger fully.\n", accepted);
  else
    g_print("  Accepted %d/12; lift finger fully.\n", accepted);
  (void) device;
  (void) print;
  (void) userdata;
}

static FpDevice *find_ft5955(FpContext *context) {
  GPtrArray *list;
  fp_context_enumerate(context);
  list = fp_context_get_devices(context);
  for (guint i = 0; i < list->len; i++) {
    FpDevice *item = g_ptr_array_index(list, i);
    if (g_strcmp0(fp_device_get_driver(item), "focaltech_5955") == 0)
      return item;
  }
  return NULL;
}

static gboolean close_device(FpDevice *device) {
  g_autoptr(GError) err = NULL;
  if (device && fp_device_is_open(device) &&
      !fp_device_close_sync(device, NULL, &err)) {
    g_printerr("Device close failed: %s\n", err ? err->message : "unknown");
    return FALSE;
  }
  return TRUE;
}

int main(int argc, char **argv) {
  g_autoptr(FpContext) context = NULL;
  g_autoptr(FpPrint) enrolled = NULL;
  g_autoptr(FpPrint) restored = NULL;
  g_autoptr(GError) error = NULL;
  guchar *serialized = NULL;
  gsize serialized_len = 0;
  FpDevice *device = NULL; /* borrowed from context */
  int ret = 1;
  unsigned unexpected = 0;
  static const struct {
    const char *label;
    gboolean expected;
  } trials[] = {
    {"ENROLLED finger", TRUE},
    {"DIFFERENT finger", FALSE},
    {"ANOTHER DIFFERENT finger", FALSE},
    {"ENROLLED finger again", TRUE},
  };

  if (argc != 2 || strcmp(argv[1], "--live") != 0) {
    fputs("Usage: native_print_roundtrip --live (normal user only)\n", stderr);
    return 2;
  }
  if (g_strcmp0(g_getenv("FT5955_EXPERIMENTAL_ENABLE"), "1") != 0 ||
      !g_getenv("FT5955_ENGINE_GATEWAY") ||
      g_getenv("FT5955_ENGINE_GATEWAY")[0] != '/') {
    fputs("Explicit FT5955_EXPERIMENTAL_ENABLE=1 and absolute FT5955_ENGINE_GATEWAY required.\n", stderr);
    return 2;
  }
  if (geteuid() == 0) {
    fputs("Do not run this test under sudo/root.\n", stderr);
    return 2;
  }
  g_print("FT5955 native FpPrint roundtrip / negative controls (experimental).\n"
          "12 accepted enrolment samples, in-memory libfprint serialise/restore,\n"
          "close/reopen device, then four labelled fresh tests.\n"
          "No data files, fprintd, PAM or system install. q cancels at prompts.\n");
  if (!ask("Finger OFF sensor. Enter to begin enrolment (q to quit): ")) {
    ret = 0;
    goto cleanup;
  }
  context = fp_context_new();
  device = find_ft5955(context);
  if (!device) {
    fputs("Private libfprint did not find focaltech_5955.\n", stderr);
    goto cleanup;
  }
  if (!fp_device_open_sync(device, NULL, &error)) {
    g_printerr("Device open failed: %s\n", error->message);
    goto cleanup;
  }
  g_print("Place the SAME finger for all 12 accepted samples; lift fully between captures.\n");
  enrolled = fp_device_enroll_sync(device, fp_print_new(device), NULL,
                                  on_enroll, NULL, &error);
  if (!enrolled) {
    g_printerr("Enrol failed: %s\n", error ? error->message : "unknown");
    goto cleanup;
  }
  if (!fp_print_serialize(enrolled, &serialized, &serialized_len, &error)) {
    g_printerr("Real print serialisation failed: %s\n", error ? error->message : "unknown");
    goto cleanup;
  }
  if (!serialized || !serialized_len || serialized_len > MAX_SERIALIZED) {
    g_printerr("Serialized print rejected (unexpected length).\n");
    goto cleanup;
  }
  g_print("Native FpPrint serialised in RAM (size withheld).\n");
  /* The original FpPrint is deliberately destroyed, and the libfprint
   * context/device are closed before restoration into a new context. */
  g_clear_object(&enrolled);
  if (!close_device(device)) goto cleanup;
  device = NULL;
  g_clear_object(&context);

  restored = fp_print_deserialize(serialized, serialized_len, &error);
  wipe(serialized, serialized_len);
  g_free(serialized);
  serialized = NULL;
  serialized_len = 0;
  if (!restored) {
    g_printerr("Real print deserialisation failed: %s\n", error ? error->message : "unknown");
    goto cleanup;
  }
  if (g_strcmp0(fp_print_get_driver(restored), "focaltech_5955") != 0 ||
      fp_print_get_device_stored(restored)) {
    g_printerr("Restored FpPrint metadata is incompatible.\n");
    goto cleanup;
  }
  context = fp_context_new();
  device = find_ft5955(context);
  if (!device || !fp_device_open_sync(device, NULL, &error)) {
    g_printerr("Open after FpPrint restore failed: %s\n",
               error ? error->message : "reader missing");
    goto cleanup;
  }
  g_print("PASS: real FpPrint restored into a NEW libfprint device/context, RAM only.\n");

  for (guint i = 0; i < G_N_ELEMENTS(trials); i++) {
    g_autofree gchar *question = g_strdup_printf(
      "[%u/%u] Lift OFF. Enter, then touch with %s (q to quit): ",
      i+1, (unsigned)G_N_ELEMENTS(trials), trials[i].label);
    gboolean match = FALSE;
    if (!ask(question)) {
      g_print("Operator stopped session.\n");
      ret = 0;
      goto cleanup;
    }
    g_print("  Now place %s on the sensor.\n", trials[i].label);
    g_clear_error(&error);
    if (!fp_device_verify_sync(device, restored, NULL, NULL, NULL,
                               &match, NULL, &error)) {
      g_printerr("  Verification operation failed: %s\n",
                 error ? error->message : "unknown");
      goto cleanup;
    }
    g_print("  Result: %s; expected: %s — %s\n",
            match ? "MATCH" : "NO_MATCH",
            trials[i].expected ? "MATCH" : "NO_MATCH",
            match == trials[i].expected ? "PASS" : "UNEXPECTED");
    if (match != trials[i].expected) unexpected++;
  }
  if (unexpected) {
    g_printerr("ATTENTION: %u unexpected verification result(s); not validated for authentication.\n",
               unexpected);
    ret = 8;
  } else {
    g_print("PASS: real native libfprint FpPrint roundtrip plus 2 expected matches / 2 expected no-matches.\n");
    ret = 0;
  }
cleanup:
  if (!close_device(device)) ret = 9;
  device = NULL;
  if (serialized) {
    wipe(serialized, serialized_len);
    g_free(serialized);
  }
  /* Unref is not a guaranteed secure memory wipe of GLib/GVariant buffers. */
  g_clear_object(&restored);
  g_clear_object(&enrolled);
  g_clear_object(&context);
  return ret;
}
