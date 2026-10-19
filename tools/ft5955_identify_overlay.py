#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Opt-in libfprint identify overlay for a DISPOSABLE reconstructed FT5955 source.

Does not edit the checksum-verified historical snapshot or a live driver tree.
The existing verify/enroll and their latency/timing transforms stay unchanged.
One observed fresh touch is compared against each print in the gallery, using
the existing protected MODE V / FRAME engine protocol in separate sessions.
This source-only variant MUST be compiled and reviewed before any installation.
"""
from __future__ import annotations

from pathlib import Path

DRIVER = Path("libfprint/drivers/focaltech_5955.c")
HEADER = Path("libfprint/drivers/ft5955_native_action.h")
ACTION = Path("libfprint/drivers/ft5955_native_action.c")

IDENTIFY_C = r'''
/*
 * FT5955 gallery identification (opt-in reconstruction variant).
 * Never perform USB acquisition more than once per candidate gallery pass.
 * libfprint supplies the current account's enrolled gallery: no cross-user
 * searches, guessed finger labels, re-enrolment, or relaxed MATCH decisions.
 *
 * This is intentionally separate from the already proven VERIFY worker.
 * The caller still uses the same pinned and isolated MOH protocol service.
 */
#define FT5955_MAX_IDENTIFY_GALLERY 20u
#define FT5955_MAX_IDENTIFY_CAPTURE 16u

typedef enum {
  FT5955_IDENTIFY_ERROR = -1,
  FT5955_IDENTIFY_NO_MATCH = 0,
  FT5955_IDENTIFY_MATCH = 1,
  FT5955_IDENTIFY_RETRY = 2
} FtIdentifyDecision;

typedef struct {
  GUsbDevice *usb;
  GPtrArray *prints;                 /* owned refs to supplied gallery entries */
  Ft5955PrintTemplate *templates;  /* copied + cleared on final task release */
  guint length;
  gint match_index;                 /* -1 means no matching gallery entry */
} FtIdentifyJob;

static void
ft5955_identify_job_free (gpointer data)
{
  FtIdentifyJob *job = data;
  if (!job)
    return;
  if (job->templates)
    {
      for (guint i = 0; i < job->length; i++)
        ft5955_print_template_clear (&job->templates[i]);
      g_free (job->templates);
    }
  if (job->prints)
    g_ptr_array_unref (job->prints);
  g_clear_object (&job->usb);
  g_free (job);
}

/* No changes to the existing root-only relay, socket, template format or DLL.
 * Start a NEW bounded verification session for each stored gallery print.
 * This is required because MODE V imports exactly one template per session. */
static FtIdentifyDecision
ft5955_identify_try (const Ft5955PrintTemplate *tmpl,
                     const guint8 frame[FT5955_PIXELS],
                     GCancellable *c,
                     GError **err)
{
  FtIdentifyDecision result = FT5955_IDENTIFY_ERROR;
  GSubprocess *child = NULL;
  GInputStream *in = NULL;
  GOutputStream *out = NULL;
  FtJob borrowed = { 0 };
  gchar *reply = NULL;

  borrowed.enrolling = FALSE;
  borrowed.candidate = *tmpl;
  if (!start_gateway (&borrowed, &child, &in, &out, c, err) ||
      !startup (&borrowed, in, out, c, err))
    goto cleanup;

  if (!write_all (out, "FRAME\n", 6, c, err) ||
      !write_all (out, frame, FT5955_PIXELS, c, err))
    goto cleanup;
  reply = read_line (G_DATA_INPUT_STREAM (in), c, err);
  if (!reply)
    goto cleanup;
  if (strcmp (reply, "MATCH") == 0)
    result = FT5955_IDENTIFY_MATCH;
  else if (strcmp (reply, "NO_MATCH") == 0)
    result = FT5955_IDENTIFY_NO_MATCH;
  else if (strcmp (reply, "RETRY QUALITY") == 0)
    result = FT5955_IDENTIFY_RETRY;
  else
    g_set_error_literal (err, G_IO_ERROR, G_IO_ERROR_INVALID_DATA,
                         "Invalid FT5955 identification reply");

cleanup:
  g_free (reply);
  if (child)
    {
      if (out && g_subprocess_get_identifier (child) != NULL)
        {
          gsize ignored = 0;
          (void) g_output_stream_write_all (out, "QUIT\n", 5, &ignored,
                                            NULL, NULL);
        }
      gint64 limit = g_get_monotonic_time () + 10 * G_USEC_PER_SEC;
      while (g_subprocess_get_identifier (child) != NULL &&
             g_get_monotonic_time () < limit)
        g_usleep (20000);
      if (g_subprocess_get_identifier (child) != NULL)
        {
          g_subprocess_send_signal (child, SIGTERM);
          limit = g_get_monotonic_time () + 3 * G_USEC_PER_SEC;
          while (g_subprocess_get_identifier (child) != NULL &&
                 g_get_monotonic_time () < limit)
            g_usleep (20000);
        }
      if (g_subprocess_get_identifier (child) != NULL)
        {
          /* A gateway that cannot exit promptly must not authorise anyone. */
          if (err && !*err)
            g_set_error_literal (err, G_IO_ERROR, G_IO_ERROR_TIMED_OUT,
                                 "FT5955 identify gateway cleanup timed out");
          g_subprocess_force_exit (child);
        }
      gboolean exited = g_subprocess_wait (child, NULL, NULL);
      if ((!exited || !g_subprocess_get_successful (child)) && err && !*err)
        g_set_error_literal (err, G_IO_ERROR, G_IO_ERROR_FAILED,
                             "FT5955 identify gateway exited unsuccessfully");
      g_object_unref (child);
    }
  if (in)
    g_object_unref (in);
  if (c && err && !*err && g_cancellable_set_error_if_cancelled (c, err))
    return FT5955_IDENTIFY_ERROR;
  if (err && *err)
    return FT5955_IDENTIFY_ERROR;
  return result;
}

static void
ft5955_identify_worker (GTask *task,
                        gpointer source,
                        gpointer data,
                        GCancellable *c)
{
  FtIdentifyJob *job = data;
  GError *err = NULL;
  guint8 frame[FT5955_PIXELS] = { 0 };
  gboolean decided = FALSE;

  for (guint attempt = 0; attempt < FT5955_MAX_IDENTIFY_CAPTURE; attempt++)
    {
      gboolean retry = FALSE;
      if (c && g_cancellable_set_error_if_cancelled (c, &err))
        goto finish;
      if (!ft5955_native_scan (job->usb, c, frame, &err))
        goto finish;

      /* Re-use this same captured frame for ALL enrolled prints. */
      for (guint i = 0; i < job->length; i++)
        {
          FtIdentifyDecision verdict = ft5955_identify_try (
              &job->templates[i], frame, c, &err);
          if (verdict == FT5955_IDENTIFY_ERROR)
            goto finish;
          if (verdict == FT5955_IDENTIFY_RETRY)
            {
              retry = TRUE;
              break;  /* rejected image: require a fresh touch */
            }
          if (verdict == FT5955_IDENTIFY_MATCH)
            {
              job->match_index = (gint) i;
              decided = TRUE;
              break;
            }
          /* Genuine NO_MATCH: test the next gallery print, not a new touch. */
        }
      sensitive_clear (frame, sizeof frame);
      if (decided || !retry)
        {
          decided = TRUE; /* includes complete, genuine gallery NO_MATCH */
          break;
        }
    }
  if (!decided)
    g_set_error_literal (&err, G_IO_ERROR, G_IO_ERROR_TIMED_OUT,
                         "FT5955 identification capture limit reached");
finish:
  sensitive_clear (frame, sizeof frame);
  if (c && !err && g_cancellable_is_cancelled (c))
    g_cancellable_set_error_if_cancelled (c, &err);
  if (err)
    g_task_return_error (task, err);
  else
    g_task_return_boolean (task, TRUE);
  (void) source;
}

static void
ft5955_identify_finish (GObject *source,
                        GAsyncResult *res,
                        gpointer unused)
{
  FpDevice *dev = FP_DEVICE (source);
  GTask *task = G_TASK (res);
  FtIdentifyJob *job = g_task_get_task_data (task);
  g_autoptr(GError) err = NULL;

  if (!g_task_propagate_boolean (task, &err))
    {
      fpi_device_identify_complete (dev, g_steal_pointer (&err));
      return;
    }

  FpPrint *match = NULL;
  if (job->match_index >= 0 &&
      (guint) job->match_index < job->prints->len)
    match = g_ptr_array_index (job->prints, (guint) job->match_index);

  /* The MOH engine supplies a verdict, not a new enrollable FpPrint.
   * No scanned print is available to return. A NULL match is a real
   * gallery NO_MATCH, never a positive result. */
  fpi_device_identify_report (dev, match, NULL, NULL);
  fpi_device_identify_complete (dev, NULL);
  (void) unused;
}

void
ft5955_native_identify (FpDevice *dev)
{
  GPtrArray *gallery = NULL;
  FtIdentifyJob *job = NULL;
  GError *err = NULL;

  if (g_strcmp0 (g_getenv ("FT5955_EXPERIMENTAL_ENABLE"), "1") != 0)
    {
      err = fpi_device_error_new_msg (FP_DEVICE_ERROR_NOT_SUPPORTED,
                    "FT5955 identification trial is disabled");
      goto fail;
    }
  fpi_device_get_identify_data (dev, &gallery);
  /* A host-template-only device cannot identify against an empty gallery. */
  if (!gallery || gallery->len == 0 ||
      gallery->len > FT5955_MAX_IDENTIFY_GALLERY)
    {
      err = fpi_device_error_new_msg (FP_DEVICE_ERROR_DATA_INVALID,
                    "FT5955 identification requires a bounded print gallery");
      goto fail;
    }

  job = g_new0 (FtIdentifyJob, 1);
  job->length = gallery->len;
  job->match_index = -1;
  job->prints = g_ptr_array_new_with_free_func (g_object_unref);
  job->templates = g_new0 (Ft5955PrintTemplate, job->length);
  job->usb = g_object_ref (fpi_device_get_usb_device (dev));

  for (guint i = 0; i < job->length; i++)
    {
      FpPrint *print = g_ptr_array_index (gallery, i);
      if (!print || !ft5955_fpprint_extract (print, &job->templates[i]))
        {
          err = fpi_device_error_new_msg (FP_DEVICE_ERROR_DATA_INVALID,
                            "FT5955 identification gallery print is invalid");
          goto fail;
        }
      g_ptr_array_add (job->prints, g_object_ref (print));
    }

  GTask *task = g_task_new (dev, fpi_device_get_cancellable (dev),
                            ft5955_identify_finish, NULL);
  g_task_set_task_data (task, job, ft5955_identify_job_free);
  g_task_set_return_on_cancel (task, FALSE);
  g_task_run_in_thread (task, ft5955_identify_worker);
  g_object_unref (task);
  return;
fail:
  ft5955_identify_job_free (job);
  fpi_device_identify_complete (dev, err);
}
'''

def apply_identify_variant(source: Path) -> None:
    """Install identify into an already reconstructed disposable libfprint tree.

    Entire replacement set is validated before writing any file. In
    particular never alter the original snapshot, current working tree, or
    installed library; caller chooses the disposable source directory.
    """
    root = source.resolve(strict=True)
    if root.is_symlink() or "libfprint" not in root.name:
        raise ValueError("Identify overlay requires a disposable libfprint source tree")

    changes = {
        DRIVER: (
            "  dev_class->verify = ft5955_native_verify;\n",
            "  dev_class->verify = ft5955_native_verify;\n"
            "  dev_class->identify = ft5955_native_identify;\n",
        ),
        HEADER: (
            "void ft5955_native_verify(FpDevice *device);\n",
            "void ft5955_native_verify(FpDevice *device);\n"
            "void ft5955_native_identify(FpDevice *device);\n",
        ),
        ACTION: (
            "void ft5955_native_verify(FpDevice *dev) { launch(dev,FALSE); }\n",
            "void ft5955_native_verify(FpDevice *dev) { launch(dev,FALSE); }\n"
            + IDENTIFY_C,
        ),
    }
    outputs: dict[Path, str] = {}
    for relative, (old, new) in changes.items():
        target = source / relative
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"Missing regular identify target: {relative}")
        original = target.read_text(encoding="utf-8")
        if original.count(old) != 1 or "ft5955_native_identify" in original:
            raise ValueError(f"Unexpected identify source anchor: {relative}")
        outputs[target] = original.replace(old, new, 1)

    # Atomicity in the scope of this disposable source: all source/anchors
    # preflighted before any file is modified.
    for target, changed in outputs.items():
        target.write_text(changed, encoding="utf-8")
