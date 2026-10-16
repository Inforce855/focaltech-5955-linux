/* SPDX-License-Identifier: LGPL-2.1-or-later
 * FT5955 MOH host-side FpPrint bridge.
 * Build this INSIDE the user's isolated libfprint checkout; NOT a plugin.
 * For a standalone private-libfprint ABI test, build with
 * -DFT5955_EXTERNAL_TEST, which uses the public GObject property to
 * change fpi-type instead of linking against hidden internal symbols.
 */
#include "ft5955_fpi_print_bridge.h"
#include "fpi-print.h"
#include <string.h>

static gboolean
is_right_print (FpPrint *print)
{
  const gchar *driver;
  if (!FP_IS_PRINT (print) || fp_print_get_device_stored (print))
    return FALSE;
  driver = fp_print_get_driver (print);
  return driver && g_strcmp0 (driver, "focaltech_5955") == 0;
}

/* Assign once, to a fresh FpPrint. A valid MOH envelope alone does not
 * grant trust in the template or make host storage safe for system login. */
gboolean
ft5955_fpprint_assign (FpPrint *print, const guint8 *envelope, gsize length)
{
  Ft5955PrintTemplate checked = { 0 };
  gint type = FPI_PRINT_UNDEFINED;
  GVariant *existing = NULL;
  GVariant *payload;
  gboolean can_assign;

  if (!is_right_print (print) || !envelope ||
      ft5955_print_unpack (envelope, length, &checked) != 0)
    return FALSE;
  ft5955_print_template_clear (&checked);

  g_object_get (print, "fpi-type", &type, "fpi-data", &existing, NULL);
  can_assign = type == FPI_PRINT_UNDEFINED && existing == NULL;
  g_clear_pointer (&existing, g_variant_unref);
  if (!can_assign)
    return FALSE;

  payload = g_variant_ref_sink (g_variant_new_fixed_array (
      G_VARIANT_TYPE_BYTE, envelope, length, sizeof (guint8)));
#ifdef FT5955_EXTERNAL_TEST
  /* The standalone ABI test cannot reference libfprint's hidden
   * fpi_print_set_type() symbol. The property is writable in 1.94.x. */
  g_object_set (print, "fpi-type", FPI_PRINT_RAW, NULL);
#else
  fpi_print_set_type (print, FPI_PRINT_RAW);
#endif
  g_object_set (print, "fpi-data", payload, NULL);
  g_variant_unref (payload);
  return TRUE;
}

/* On success OUT owns a malloc'd sensitive copy; call
 * ft5955_print_template_clear(). No raw image or vendor DLL is returned. */
gboolean
ft5955_fpprint_extract (FpPrint *print, Ft5955PrintTemplate *out)
{
  gint type = FPI_PRINT_UNDEFINED;
  GVariant *payload = NULL;
  const guint8 *bytes;
  gsize length = 0;
  gboolean success;

  if (!out)
    return FALSE;
  memset (out, 0, sizeof (*out));
  if (!is_right_print (print))
    return FALSE;
  g_object_get (print, "fpi-type", &type, "fpi-data", &payload, NULL);
  if (type != FPI_PRINT_RAW || !payload)
    {
      g_clear_pointer (&payload, g_variant_unref);
      return FALSE;
    }
  if (!g_variant_is_of_type (payload, G_VARIANT_TYPE ("ay")))
    {
      g_variant_unref (payload);
      return FALSE;
    }
  bytes = g_variant_get_fixed_array (payload, &length, sizeof (guint8));
  success = bytes && ft5955_print_unpack (bytes, length, out) == 0;
  g_variant_unref (payload);
  return success;
}
