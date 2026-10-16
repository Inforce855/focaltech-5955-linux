/* SPDX-License-Identifier: LGPL-2.1-or-later
 * ACTUAL private-libfprint FpPrint serialization test with SYNTHETIC bytes.
 * Does not enumerate or open any USB device or save print data to disk.
 */
#include "ft5955_fpi_print_bridge.h"
#include "fpi-print.h"
#include <glib.h>
#include <stdio.h>
#include <string.h>

#define CHECK(cond, msg) do { if (!(cond)) { \
  g_printerr ("FAIL: %s\n", msg); return 1; } } while (0)

int
main (void)
{
  guint8 fake_template[160];
  guint8 *envelope = NULL;
  size_t envelope_len = 0;
  guchar *serialized = NULL;
  gsize serialized_len = 0;
  g_autoptr(GError) error = NULL;
  g_autoptr(FpPrint) restored = NULL;
  g_autoptr(FpPrint) other = NULL;
  Ft5955PrintTemplate decoded = {0};
  GVariant *bad_payload;

  for (size_t i = 0; i < sizeof fake_template; i++)
    fake_template[i] = (guint8) (i * 41u + 7u);
  CHECK (ft5955_print_pack (fake_template, sizeof fake_template, 2,
                             &envelope, &envelope_len) == 0, "synthetic pack");

  /* The native driver normally gets an enrollment FpPrint from libfprint.
   * This intentionally uses a manufactured object to avoid USB discovery. */
  FpPrint *obj = g_object_new (FP_TYPE_PRINT,
                               "driver", "focaltech_5955",
                               "device-id", "ft5955-synthetic-test",
                               NULL);
  CHECK (obj != NULL, "GObject construct");
  g_autoptr(FpPrint) original = g_object_ref_sink (obj);
  CHECK (ft5955_fpprint_assign (original, envelope, envelope_len), "assign to original print");
  CHECK (!ft5955_fpprint_assign (original, envelope, envelope_len), "double assign must fail");
  CHECK (!fp_print_get_device_stored (original), "host-side print must not be device stored");

  CHECK (fp_print_serialize (original, &serialized, &serialized_len, &error),
         error ? error->message : "serialize real libfprint FpPrint");
  CHECK (serialized && serialized_len, "serialized data nonempty");
  restored = fp_print_deserialize (serialized, serialized_len, &error);
  CHECK (restored != NULL, error ? error->message : "deserialize actual libfprint bytes");
  CHECK (g_strcmp0 (fp_print_get_driver (restored), "focaltech_5955") == 0,
         "driver metadata roundtrip");
  CHECK (g_strcmp0 (fp_print_get_device_id (restored), "ft5955-synthetic-test") == 0,
         "device id metadata roundtrip");
  CHECK (ft5955_fpprint_extract (restored, &decoded), "extract after libfprint restore");
  CHECK (decoded.length == sizeof fake_template && decoded.subfactor == 2 &&
         memcmp (decoded.bytes, fake_template, sizeof fake_template) == 0,
         "vendor template and subfactor roundtrip");
  ft5955_print_template_clear (&decoded);

  /* Corruption and wrong-device tests: neither may produce a usable template. */
  bad_payload = g_variant_ref_sink (g_variant_new_fixed_array (
      G_VARIANT_TYPE_BYTE, fake_template, sizeof fake_template, 1));
  g_object_set (restored, "fpi-data", bad_payload, NULL);
  g_variant_unref (bad_payload);
  CHECK (!ft5955_fpprint_extract (restored, &decoded), "reject malformed payload");
  other = g_object_ref_sink (g_object_new (FP_TYPE_PRINT,
                       "driver", "different_driver",
                       "device-id", "ft5955-synthetic-test", NULL));
  CHECK (!ft5955_fpprint_assign (other, envelope, envelope_len), "reject different driver");

  ft5955_free_sensitive (envelope, envelope_len);
  memset (fake_template, 0, sizeof fake_template);
  /* g_clear_pointer frees libfprint's serialized buffer (including the
   * synthetic secret); no file is ever created. */
  if (serialized)
    {
      volatile guint8 *p = serialized;
      for (gsize i = 0; i < serialized_len; ++i) p[i] = 0;
      g_free (serialized);
    }
  puts ("PASS: real private libfprint FpPrint RAW serialization/deserialization, metadata and validation");
  return 0;
}
