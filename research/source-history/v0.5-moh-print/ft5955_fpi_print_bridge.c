/* SPDX-License-Identifier: LGPL-2.1-or-later
 * INTEGRATION SOURCE ONLY: requires libfprint's internal drivers_api.h and
 * GLib, and should be built in the user's private libfprint source tree.
 * NOT compiled or validated in the synthetic codec test environment.
 *
 * Call ft5955_fpprint_assign() only once on the fresh FpPrint supplied by
 * fpi_device_get_enroll_data(); for a print deserialised from storage use
 * ft5955_fpprint_extract(), which rejects incompatible/tampered print data.
 * FPI_PRINT_RAW means HOST-SIDE raw/opaque matching here; templates must NOT
 * be marked device-stored (this is a match-on-HOST reader).
 */
#include "drivers_api.h"
#include "ft5955_print_codec.h"

/* envelope bytes are sensitive; GVariant/libfprint may make memory copies. */
gboolean ft5955_fpprint_assign(FpPrint *print, const uint8_t *envelope, size_t n) {
  Ft5955PrintTemplate check={0};
  if (!FP_IS_PRINT(print) || ft5955_print_unpack(envelope,n,&check)) return FALSE;
  ft5955_print_template_clear(&check);
  fpi_print_set_type(print, FPI_PRINT_RAW);
  GVariant *payload = g_variant_ref_sink(
      g_variant_new_fixed_array(G_VARIANT_TYPE_BYTE, envelope, n, 1));
  g_object_set(G_OBJECT(print), "fpi-data", payload, NULL);
  g_variant_unref(payload);
  return TRUE;
}

/* Produces a sensitive malloc'd, validated COPY; caller must wipe and free. */
gboolean ft5955_fpprint_extract(FpPrint *print, Ft5955PrintTemplate *result) {
  if (!FP_IS_PRINT(print) || !result) return FALSE;
  GVariant *payload=NULL;
  g_object_get(G_OBJECT(print), "fpi-data", &payload, NULL);
  if (!payload) return FALSE;
  if (!g_variant_is_of_type(payload,G_VARIANT_TYPE("ay"))) {
    g_variant_unref(payload); return FALSE;
  }
  gsize n=0;
  const guint8 *bytes=g_variant_get_fixed_array(payload,&n,sizeof(guint8));
  gboolean ok=(bytes && ft5955_print_unpack(bytes,n,result)==0);
  g_variant_unref(payload);
  return ok;
}
