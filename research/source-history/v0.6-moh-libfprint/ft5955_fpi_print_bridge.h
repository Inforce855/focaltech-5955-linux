/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <glib-object.h>
#include "fp-print.h"
#include "ft5955_print_codec.h"

/* These helpers wrap a HOST-side FT5955 MOH template envelope.
 * The caller must use the FocalTech 5955 print driver and a freshly
 * constructed print. The envelope contains sensitive vendor template data.
 */
gboolean ft5955_fpprint_assign (FpPrint *print, const guint8 *envelope, gsize length);
gboolean ft5955_fpprint_extract (FpPrint *print, Ft5955PrintTemplate *out);
