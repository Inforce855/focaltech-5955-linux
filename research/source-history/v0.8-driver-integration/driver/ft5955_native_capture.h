/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <gio/gio.h>
#include <gusb.h>
#include <stdint.h>
#define FT5955_PIXELS 5120
/* USB interface 0 must be claimed before use; caller serialises operations.
 * Never stores a biometric frame or writes it to any file. */
gboolean ft5955_native_scan (GUsbDevice *usb, GCancellable *cancel,
                             uint8_t pixels[FT5955_PIXELS], GError **error);
