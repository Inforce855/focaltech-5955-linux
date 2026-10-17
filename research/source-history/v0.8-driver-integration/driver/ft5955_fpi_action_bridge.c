/* SPDX-License-Identifier: LGPL-2.1-or-later
 * FT5955 MOH -> libfprint callback mapping.
 * This helper is NOT an operational driver: the caller must own async USB
 * capture, lift/press transitions, sandbox life cycle, worker-thread IPC,
 * cancellation, and a main-thread callback with the real MOH result.
 */
#include "ft5955_fpi_action_bridge.h"
#include "ft5955_fpi_print_bridge.h"
#include "fpi-device.h"
#include "fpi-print.h"
#include <glib.h>
#include <gio/gio.h>

static GError *
engine_error (const char *message)
{
  return fpi_device_error_new_msg (FP_DEVICE_ERROR_GENERAL, "%s", message);
}

gboolean
ft5955_fpi_apply_reply (FpDevice *device, Ft5955Action *action,
                        const char *moh_reply,
                        const uint8_t *vendor_template,
                        size_t vendor_template_len,
                        uint8_t subfactor)
{
  Ft5955DriverEvent result;
  unsigned stage = 0;
  if (!device || !action || !moh_reply)
    return FALSE;
  /* All fpi_device_* calls must be marshalled to the device main context. */
  result = ft5955_action_consume_reply (action, moh_reply, &stage);
  if (result == FT5955_DRIVER_INVALID)
    return FALSE;
  if (action->kind == FT5955_ACTION_ENROLL)
    {
      if (result == FT5955_DRIVER_PROGRESS)
        {
          fpi_device_enroll_progress (device, (gint) stage, NULL, NULL);
          return TRUE;
        }
      if (result == FT5955_DRIVER_RETRY)
        {
          fpi_device_enroll_progress (device, (gint) stage, NULL,
                                      fpi_device_retry_new (FP_DEVICE_RETRY_GENERAL));
          return TRUE;
        }
      if (result == FT5955_DRIVER_ENROLLED)
        {
          FpPrint *print = NULL;
          uint8_t *envelope = NULL;
          size_t envelope_len = 0;
          gboolean assigned = FALSE;
          /* Enrol data is libfprint-owned. Do not free the template print. */
          fpi_device_get_enroll_data (device, &print);
          if (print && vendor_template && vendor_template_len > 0 &&
              ft5955_print_pack (vendor_template, vendor_template_len,
                                 subfactor, &envelope, &envelope_len) == 0)
            assigned = ft5955_fpprint_assign (print, envelope, envelope_len);
          if (envelope)
            ft5955_free_sensitive (envelope, envelope_len);
          if (!assigned)
            {
              fpi_device_enroll_complete (device, NULL,
                                          engine_error ("FT5955 MOH print creation failed"));
              return FALSE;
            }
          /* The final progress must be followed by exactly one completion. */
          fpi_device_enroll_progress (device, (gint) stage, NULL, NULL);
          fpi_device_enroll_complete (device, g_object_ref (print), NULL);
          return FALSE;
        }
      fpi_device_enroll_complete (device, NULL,
                                  result == FT5955_DRIVER_CANCELLED
                                      ? g_error_new_literal (G_IO_ERROR, G_IO_ERROR_CANCELLED,
                                                             "FT5955 enrolment cancelled")
                                      : engine_error ("FT5955 enrolment failed or protocol mismatch"));
      return FALSE;
    }

  if (action->kind == FT5955_ACTION_VERIFY)
    {
      if (result == FT5955_DRIVER_RETRY)
        {
          fpi_device_verify_report (device, FPI_MATCH_ERROR, NULL,
                                     fpi_device_retry_new (FP_DEVICE_RETRY_GENERAL));
          return TRUE; /* Another fresh scan is needed. */
        }
      if (result == FT5955_DRIVER_MATCHED || result == FT5955_DRIVER_NOT_MATCHED)
        {
          fpi_device_verify_report (device,
                                    result == FT5955_DRIVER_MATCHED ? FPI_MATCH_SUCCESS
                                                                    : FPI_MATCH_FAIL,
                                    NULL, NULL);
          fpi_device_verify_complete (device, NULL);
          return FALSE;
        }
      fpi_device_verify_complete (device,
                                  result == FT5955_DRIVER_CANCELLED
                                      ? g_error_new_literal (G_IO_ERROR, G_IO_ERROR_CANCELLED,
                                                             "FT5955 verification cancelled")
                                      : engine_error ("FT5955 verification failed or protocol mismatch"));
      return FALSE;
    }
  return FALSE;
}
