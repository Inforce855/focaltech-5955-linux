/* SPDX-License-Identifier: LGPL-2.1-or-later
 * FT5955 native libfprint v0.9.4 verify cancellation + one forced quality retry.
 * Test-only application: no driver modifications or print persistence.
 */
#include "fprint.h"
#include <gio/gio.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

typedef struct {
  GMainLoop *loop;
  GCancellable *cancel;
  guint cancel_source;
  guint watchdog_source;
  gboolean cancel_sent;
  gboolean complete;
  gboolean timed_out;
  gboolean reported_match;
  gboolean result_cancelled;
} CancelProbe;

typedef struct {
  unsigned retry_messages;
  unsigned match_reports;
  unsigned failed_reports;
} QualityProbe;

static gboolean ask(const char *prompt) {
  char response[64] = {0};
  g_print("%s", prompt);
  fflush(stdout);
  if (!fgets(response, sizeof response, stdin)) return FALSE;
  return response[0] == '\n' || response[0] == '\r';
}

static FpDevice *ft_device(FpContext *ctx) {
  fp_context_enumerate(ctx);
  GPtrArray *devices = fp_context_get_devices(ctx);
  for (guint i = 0; i < devices->len; i++) {
    FpDevice *device = g_ptr_array_index(devices, i);
    if (g_strcmp0(fp_device_get_driver(device), "focaltech_5955") == 0)
      return device;
  }
  return NULL;
}

static void enroll_progress(FpDevice *device, gint accepted, FpPrint *print,
                            gpointer data, GError *error) {
  if (error)
    g_print("  Enrol scan rejected (%d/12); lift fully.\n", accepted);
  else
    g_print("  Accepted %d/12; lift fully.\n", accepted);
  (void)device; (void)print; (void)data;
}

static gboolean cancel_verify(gpointer data) {
  CancelProbe *p = data;
  p->cancel_source = 0;
  if (!p->complete && !p->cancel_sent) {
    p->cancel_sent = TRUE;
    g_print("CANCEL REQUESTED during verification.\n");
    g_cancellable_cancel(p->cancel);
  }
  return G_SOURCE_REMOVE;
}

static gboolean verify_watchdog(gpointer data) {
  CancelProbe *p = data;
  p->watchdog_source = 0;
  if (!p->complete) {
    p->timed_out = TRUE;
    g_printerr("FAIL: verification did not finish within 35 seconds.\n");
    if (!p->cancel_sent) {
      p->cancel_sent = TRUE;
      g_cancellable_cancel(p->cancel);
    }
    g_main_loop_quit(p->loop);
  }
  return G_SOURCE_REMOVE;
}

static void on_cancel_match(FpDevice *device, FpPrint *match,
                            FpPrint *scanned, gpointer data, GError *error) {
  CancelProbe *p = data;
  p->reported_match = TRUE;
  (void)device; (void)match; (void)scanned; (void)error;
}

static void on_cancel_finish(GObject *source, GAsyncResult *result, gpointer data) {
  CancelProbe *p = data;
  g_autoptr(GError) error = NULL;
  gboolean match = FALSE;
  gboolean ok = fp_device_verify_finish(FP_DEVICE(source), result,
                                         &match, NULL, &error);
  p->complete = TRUE;
  p->result_cancelled = !ok &&
    g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED);
  if (p->result_cancelled)
    g_print("PASS: verification returned G_IO_ERROR_CANCELLED.\n");
  else
    g_printerr("FAIL: verification returned %s (match=%d).\n",
               error ? error->message : (ok ? "completed normally" : "unknown"), match);
  g_main_loop_quit(p->loop);
}

static gboolean run_verify_cancellation(FpDevice *dev, FpPrint *print,
                                         gboolean *safe_to_close) {
  CancelProbe p = {0};
  g_autoptr(GCancellable) cancel = g_cancellable_new();
  p.loop = g_main_loop_new(NULL, FALSE);
  p.cancel = cancel;
  *safe_to_close = FALSE;
  if (!ask("Keep finger OFF. Enter to start 3-second verification cancellation: ")) {
    g_main_loop_unref(p.loop);
    return FALSE;
  }
  fp_device_verify(dev, print, cancel, on_cancel_match, &p,
                   NULL, on_cancel_finish, &p);
  p.cancel_source = g_timeout_add_seconds(3, cancel_verify, &p);
  p.watchdog_source = g_timeout_add_seconds(35, verify_watchdog, &p);
  g_main_loop_run(p.loop);
  if (p.cancel_source) g_source_remove(p.cancel_source);
  if (p.watchdog_source) g_source_remove(p.watchdog_source);
  g_main_loop_unref(p.loop);
  if (!p.complete || p.timed_out) {
    g_printerr("FAIL: callback incomplete. Do not close/reopen a pending operation.\n");
    return FALSE;
  }
  *safe_to_close = TRUE;
  if (!p.cancel_sent || !p.result_cancelled || p.reported_match) {
    g_printerr("FAIL: verification cancellation did not meet all conditions.\n");
    return FALSE;
  }
  return TRUE;
}

static void on_quality_log(const gchar *domain, GLogLevelFlags level,
                           const gchar *message, gpointer data) {
  QualityProbe *p = data;
  if (g_strcmp0(message, "FT5955 scan rejected; lift and reposition finger") == 0) {
    p->retry_messages++;
    g_print("  VERIFIED DRIVER RETRY MESSAGE #%u: %s\n", p->retry_messages, message);
  } else {
    g_log_default_handler(domain, level, message, NULL);
  }
}

static void on_quality_match(FpDevice *device, FpPrint *match, FpPrint *scanned,
                             gpointer data, GError *error) {
  QualityProbe *p = data;
  p->match_reports++;
  if (error) p->failed_reports++;
  (void)device; (void)match; (void)scanned;
}

static gboolean run_forced_quality(FpDevice *dev, FpPrint *print,
                                    const gchar *proxy_path,
                                    const gchar *original_path) {
  QualityProbe p = {0};
  g_autoptr(GError) error = NULL;
  gboolean match = FALSE;
  guint handler;
  gboolean ok;

  if (!g_setenv("FT5955_ORIGINAL_ENGINE_GATEWAY", original_path, TRUE) ||
      !g_setenv("FT5955_QUALITY_PROBE_ENABLE", "1", TRUE) ||
      !g_setenv("FT5955_ENGINE_GATEWAY", proxy_path, TRUE)) {
    g_printerr("FAIL: could not install temporary diagnostic environment.\n");
    return FALSE;
  }
  g_print("Quality-retry proxy enabled FOR THIS VERIFICATION ONLY.\n"
          "The first genuine captured frame will be discarded and replaced\n"
          "with RETRY QUALITY. Lift fully, then touch again when prompted.\n");
  handler = g_log_set_handler("libfprint", G_LOG_LEVEL_MESSAGE,
                              on_quality_log, &p);
  if (!ask("Finger OFF. Enter, touch ONCE, lift after the retry message, then touch again: ")) {
    g_log_remove_handler("libfprint", handler);
    g_setenv("FT5955_ENGINE_GATEWAY", original_path, TRUE);
    g_unsetenv("FT5955_QUALITY_PROBE_ENABLE");
    g_unsetenv("FT5955_ORIGINAL_ENGINE_GATEWAY");
    return FALSE;
  }
  ok = fp_device_verify_sync(dev, print, NULL, on_quality_match, &p,
                              &match, NULL, &error);
  g_log_remove_handler("libfprint", handler);
  /* Restore gateway regardless of result, before any subsequent operation. */
  g_setenv("FT5955_ENGINE_GATEWAY", original_path, TRUE);
  g_unsetenv("FT5955_QUALITY_PROBE_ENABLE");
  g_unsetenv("FT5955_ORIGINAL_ENGINE_GATEWAY");
  g_print("Quality probe: callbacks=%u, errors=%u, driver_retry_messages=%u, result=%s.\n",
          p.match_reports, p.failed_reports, p.retry_messages,
          !ok ? "OPERATION_ERROR" : (match ? "MATCH" : "NO_MATCH"));
  /* Check retry control flow separately from biometric recognition:
   * NO_MATCH is a valid terminal verify result for a difficult scan,
   * though it is a false rejection when the enrolled finger was used. */
  if (!ok || p.retry_messages != 1 || p.match_reports != 1 ||
      p.failed_reports != 0) {
    g_printerr("FAIL: expected one internal quality retry and one terminal "
               "verification result. %s\n",
               error ? error->message : "");
    return FALSE;
  }
  g_print("PASS: forced quality retry recovered; one terminal %s in SAME operation.\n",
          match ? "MATCH" : "NO_MATCH");
  if (!match)
    g_print("ATTENTION: enrolled finger was NOT recognised on the final scan; "
            "retry control flow passed, matching reliability did not.\n");
  return TRUE;
}

int main(int argc, char **argv) {
  g_autoptr(FpContext) ctx = NULL;
  g_autoptr(FpPrint) enrolled = NULL;
  g_autoptr(GError) error = NULL;
  g_autofree gchar *original_path = NULL;
  g_autofree gchar *proxy_path = NULL;
  FpDevice *dev = NULL;
  gboolean safe_to_close = TRUE;
  int status = 1;
  const char *gateway = g_getenv("FT5955_ENGINE_GATEWAY");
  const char *proxy = g_getenv("FT5955_QUALITY_PROBE_GATEWAY");
  if (argc != 2 || strcmp(argv[1], "--live") != 0) {
    fputs("Usage: native_verify_safety_v094 --live\n", stderr);
    return 2;
  }
  if (geteuid() == 0 ||
      g_strcmp0(g_getenv("FT5955_EXPERIMENTAL_ENABLE"), "1") != 0 ||
      !gateway || !g_path_is_absolute(gateway) ||
      !proxy || !g_path_is_absolute(proxy) ||
      !g_file_test(gateway, G_FILE_TEST_IS_REGULAR) ||
      !g_file_test(proxy, G_FILE_TEST_IS_REGULAR) ||
      g_strcmp0(gateway, proxy) == 0) {
    fputs("STOP: no root, opt-in and two distinct absolute gateway paths required.\n", stderr);
    return 2;
  }
  original_path = g_strdup(gateway);
  proxy_path = g_strdup(proxy);
  g_print("FT5955 v0.9.4 verification safety diagnostic; one RAM-only enrolment.\n"
          "No templates written to disk, no system libfprint, no fprintd/PAM.\n");
  if (!ask("Finger OFF sensor. Press Enter to enrol once (12 accepted impressions): "))
    return 2;
  ctx = fp_context_new();
  dev = ft_device(ctx);
  if (!dev || !fp_device_open_sync(dev, NULL, &error)) {
    g_printerr("FAIL: cannot open FT5955: %s\n", error ? error->message : "not found");
    return 3;
  }
  g_print("Enrol the SAME finger in twelve good, lifted touches.\n");
  enrolled = fp_device_enroll_sync(dev, fp_print_new(dev), NULL,
                                   enroll_progress, NULL, &error);
  if (!enrolled) {
    g_printerr("FAIL: enrolment: %s\n", error ? error->message : "unknown");
    goto cleanup;
  }
  g_print("PASS: 12-stage enrolment complete (RAM only).\n");

  if (!run_verify_cancellation(dev, enrolled, &safe_to_close)) {
    status = 4;
    goto cleanup;
  }
  g_print("PASS: verify cancellation while waiting for finger.\n");
  if (!fp_device_close_sync(dev, NULL, &error)) {
    g_printerr("FAIL: close after cancel: %s\n", error->message);
    status = 5; goto cleanup;
  }
  g_clear_error(&error);
  if (!fp_device_open_sync(dev, NULL, &error)) {
    g_printerr("FAIL: reopen after cancel: %s\n", error->message);
    status = 5; goto cleanup;
  }
  g_print("PASS: closed/reopened device after cancelled verification.\n");

  if (!run_forced_quality(dev, enrolled, proxy_path, original_path)) {
    status = 6; goto cleanup;
  }
  status = 0;
  g_print("PASS: v0.9.4 cancellation and quality-retry control-flow diagnostics passed.\n");
cleanup:
  if (!safe_to_close) {
    g_printerr("STOP: pending operation timed out; skipping close/unref. Terminating process.\n");
    _exit(status ? status : 10);
  }
  if (dev && fp_device_is_open(dev)) {
    g_clear_error(&error);
    if (!fp_device_close_sync(dev, NULL, &error)) {
      g_printerr("FAIL: final close: %s\n", error->message);
      status = 9;
    }
  }
  return status;
}
