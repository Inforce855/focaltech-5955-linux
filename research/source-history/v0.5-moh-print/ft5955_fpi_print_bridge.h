/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include "drivers_api.h"
#include "ft5955_print_codec.h"
gboolean ft5955_fpprint_assign(FpPrint *print, const uint8_t *envelope, size_t n);
gboolean ft5955_fpprint_extract(FpPrint *print, Ft5955PrintTemplate *result);
