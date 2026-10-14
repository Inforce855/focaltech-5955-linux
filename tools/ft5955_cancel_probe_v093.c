/* SPDX-License-Identifier: LGPL-2.1-or-later
 * FT5955 v0.9.3: opt-in libfprint async cancellation probe.
 * Test client only. No driver changes, fingerprint templates on disk,
 * fprintd/PAM calls, network operations, or privileged commands.
 */
#include "fprint.h"
#include <gio/gio.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

typedef enum { CANCEL_WITHOUT_TOUCH, CANCEL_AFTER_ONE } ProbeMode;

typedef struct {
  GMainLoop *loop;
  GCancellable *cancel;
  ProbeMode mode;
  guint cancel_source;
  guint watchdog_source;
  unsigned accepted;
  unsigned rejected;
  gboolean cancellation_sent;
  gboolean finished;
  gboolean timed_out;
  gboolean unexpected_progress;
  gboolean cancellation_confirmed;
} Probe;

static gboolean
ask_enter (const char *prompt)
{
  char input[64] = {0};
  g_print ("%s", prompt);
  fflush (stdout);
  if (!fgets (input, sizeof input, stdin))
    return FALSE;
  return input[0] == '\n' || input[0] == '\r';
}

static FpDevice *
find_reader (FpContext *ctx)
{
  fp_context_enumerate (ctx);
  GPtrArray *devices = fp_context_get_devices (ctx);
  for (guint i = 0; i < devices->len; i++)
    {
      FpDevice *dev = g_ptr_array_index (devices, i);
      if (g_strcmp0 (fp_device_get_driver (dev), "focaltech_5955") == 0)
        return dev; /* Borrowed; owned by FpContext. */
    }
  return NULL;
}

static gboolean
send_cancel (gpointer data)
{
  Probe *probe = data;
  probe->cancel_source = 0;
  if (!probe->finished && !probe->cancellation_sent)
    {
      probe->cancellation_sent = TRUE;
      g_print ("CANCEL REQUESTED via GCancellable; waiting for driver cleanup...\n");
      g_cancellable_cancel (probe->cancel);
    }
  return G_SOURCE_REMOVE;
}

static gboolean
watchdog (gpointer data)
{
  Probe *probe = data;
  probe->watchdog_source = 0;
  if (!probe->finished)
    {
      probe->timed_out = TRUE;
      g_printerr ("FAIL: enrolment callback did not complete within the watchdog.\n");
      /* Attempt cancellation, but NEVER claim recovery if completion was absent. */
      if (!probe->cancellation_sent)
        {
          probe->cancellation_sent = TRUE;
          g_cancellable_cancel (probe->cancel);
        }
      g_main_loop_quit (probe->loop);
    }
  return G_SOURCE_REMOVE;
}

static void
on_progress (FpDevice *dev, gint stages, FpPrint *print,
             gpointer user_data, GError *error)
{
  Probe *probe = user_data;
  if (error)
    {
      probe->rejected++;
      g_print ("  Enrol retry (accepted %d/12); no template saved.\n", stages);
    }
  else
    {
      probe->accepted = (unsigned) stages;
      g_print ("  Accepted %d/12.\n", stages);
      if (probe->mode == CANCEL_WITHOUT_TOUCH)
        {
          probe->unexpected_progress = TRUE;
          g_printerr ("Unexpected finger capture in no-touch test!\n");
        }
      if (probe->mode == CANCEL_AFTER_ONE && stages >= 1)
        g_print ("  First impression accepted; requesting cancellation.\n");
      if ((probe->mode == CANCEL_AFTER_ONE && stages >= 1) ||
          probe->mode == CANCEL_WITHOUT_TOUCH)
        {
          /* Do not cancel re-entrantly within libfprint's progress callback. */
          if (!probe->cancel_source && !probe->cancellation_sent)
            probe->cancel_source = g_idle_add (send_cancel, probe);
        }
    }
  (void) dev;
  (void) print;
}

static void
on_finished (GObject *source, GAsyncResult *result, gpointer user_data)
{
  Probe *probe = user_data;
  g_autoptr(GError) error = NULL;
  FpPrint *print = fp_device_enroll_finish (FP_DEVICE (source), result, &error);
  probe->finished = TRUE;
  probe->cancellation_confirmed =
      !print && probe->cancellation_sent &&
      g_error_matches (error, G_IO_ERROR, G_IO_ERROR_CANCELLED);
  if (print)
    {
      g_printerr ("FAIL: enrolment completed unexpectedly instead of cancelling.\n");
      g_object_unref (print);
    }
  else if (probe->cancellation_confirmed)
    g_print ("PASS: libfprint returned G_IO_ERROR_CANCELLED.\n");
  else
    g_printerr ("FAIL: expected G_IO_ERROR_CANCELLED; got: %s\n",
                error ? error->message : "(no error)");
  g_main_loop_quit (probe->loop);
}

int
main (int argc, char **argv)
{
  g_autoptr(FpContext) ctx = NULL;
  g_autoptr(GCancellable) cancel = NULL;
  g_autoptr(GError) error = NULL;
  FpDevice *dev;
  Probe probe = {0};
  int status = 1;

  if (argc != 2 ||
      (strcmp (argv[1], "--live-no-touch") != 0 &&
       strcmp (argv[1], "--live-after-one") != 0))
    {
      fputs ("Usage: cancel_probe_v093 --live-no-touch | --live-after-one\n"
             "Must run as a normal user against the private libfprint build.\n", stderr);
      return 2;
    }
  if (geteuid () == 0 ||
      g_strcmp0 (g_getenv ("FT5955_EXPERIMENTAL_ENABLE"), "1") != 0 ||
      !g_getenv ("FT5955_ENGINE_GATEWAY") ||
      !g_path_is_absolute (g_getenv ("FT5955_ENGINE_GATEWAY")))
    {
      fputs ("STOP: no root; require FT5955_EXPERIMENTAL_ENABLE=1 and"
             " absolute FT5955_ENGINE_GATEWAY.\n", stderr);
      return 2;
    }
  probe.mode = strcmp (argv[1], "--live-after-one") == 0
                 ? CANCEL_AFTER_ONE : CANCEL_WITHOUT_TOUCH;
  g_print ("FT5955 v0.9.3 cancellation probe (RAM-only, no system install).\n"
           "No template is exported or persisted. Do not use sudo.\n");
  if (probe.mode == CANCEL_WITHOUT_TOUCH)
    {
      if (!ask_enter ("Remove ALL fingers. Press Enter to start; keep finger OFF: "))
        return 2;
    }
  else
    {
      if (!ask_enter ("Finger OFF. Enter, then press ONCE and lift fully: "))
        return 2;
    }

  ctx = fp_context_new ();
  dev = find_reader (ctx);
  if (!dev)
    {
      fputs ("FAIL: FT5955 not found in private libfprint.\n", stderr);
      return 3;
    }
  if (!fp_device_open_sync (dev, NULL, &error))
    {
      g_printerr ("FAIL: opening reader: %s\n", error->message);
      return 4;
    }
  probe.loop = g_main_loop_new (NULL, FALSE);
  probe.cancel = cancel = g_cancellable_new ();
  /* FpPrint parameter is transfer-floating to libfprint. */
  fp_device_enroll (dev, fp_print_new (dev), cancel,
                    on_progress, &probe, NULL, on_finished, &probe);
  if (probe.mode == CANCEL_WITHOUT_TOUCH)
    probe.cancel_source = g_timeout_add_seconds (3, send_cancel, &probe);
  /* Watchdogs detect a hang; they are NOT evidence of successful cancellation. */
  probe.watchdog_source = g_timeout_add_seconds (
      probe.mode == CANCEL_WITHOUT_TOUCH ? 35 : 100, watchdog, &probe);
  g_main_loop_run (probe.loop);
  if (probe.cancel_source)
    g_source_remove (probe.cancel_source);
  if (probe.watchdog_source)
    g_source_remove (probe.watchdog_source);

  if (!probe.finished || probe.timed_out)
    {
      g_printerr ("FAIL: worker did not complete cleanly; skip close/reopen.\n"
                  "Inspect stray gateway/bwrap processes before retesting.\n");
      status = 10;
      goto end; /* Process termination is safer than a synchronous close here. */
    }
  if (!probe.cancellation_confirmed || probe.unexpected_progress ||
      (probe.mode == CANCEL_WITHOUT_TOUCH && probe.accepted != 0) ||
      (probe.mode == CANCEL_AFTER_ONE && probe.accepted != 1))
    {
      g_printerr ("FAIL: unexpected cancellation result or accepted stage count.\n");
      status = 8;
    }
  else
    status = 0;

  /* Only issue another device operation when the previous callback completed. */
  g_clear_error (&error);
  if (!fp_device_close_sync (dev, NULL, &error))
    {
      g_printerr ("FAIL: close after cancellation: %s\n", error->message);
      status = 9;
      goto end;
    }
  g_clear_error (&error);
  if (!fp_device_open_sync (dev, NULL, &error))
    {
      g_printerr ("FAIL: reopen after cancellation: %s\n", error->message);
      status = 9;
      goto end;
    }
  g_print ("PASS: reader closed and reopened after cancellation.\n");
  g_clear_error (&error);
  if (!fp_device_close_sync (dev, NULL, &error))
    {
      g_printerr ("FAIL: final close: %s\n", error->message);
      status = 9;
    }
  if (!status)
    g_print ("PASS: cancellation diagnostic completed; no persistent print.\n");
end:
  if (probe.loop)
    g_main_loop_unref (probe.loop);
  /* 'cancel' is auto-unreffed; probe.cancel is a borrowed alias. */
  return status;
}
