/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Experimental FocalTech 2808:5955 discovery-only driver. */

#define FP_COMPONENT "focaltech_5955"
#include "drivers_api.h"
#include "ft5955_native_action.h"
#include <string.h>

typedef struct _FpiDeviceFocaltech5955 {
  FpDevice parent;
} FpiDeviceFocaltech5955;

typedef struct _FpiDeviceFocaltech5955Class {
  FpDeviceClass parent_class;
} FpiDeviceFocaltech5955Class;

GType fpi_device_focaltech_5955_get_type (void);

G_DEFINE_TYPE (FpiDeviceFocaltech5955,
               fpi_device_focaltech_5955, FP_TYPE_DEVICE)

static const FpIdEntry id_table[] = {
  { .vid = 0x2808, .pid = 0x5955 },
  { .vid = 0, .pid = 0 }
};

static void
dev_open (FpDevice *dev)
{
  GUsbDevice *usb = fpi_device_get_usb_device (dev);
  g_autoptr(GError) error = NULL;
  g_autoptr(FpiUsbTransfer) rx = NULL;
  g_autoptr(FpiUsbTransfer) status_tx = NULL;
  g_autoptr(FpiUsbTransfer) status_rx = NULL;
  guint8 descriptor[18] = { 0 };
  gsize received = 0;

  /* USB standard GET_DESCRIPTOR: read-only, no fingerprint data. */
  if (!g_usb_device_control_transfer (
        usb,
        G_USB_DEVICE_DIRECTION_DEVICE_TO_HOST,
        G_USB_DEVICE_REQUEST_TYPE_STANDARD,
        G_USB_DEVICE_RECIPIENT_DEVICE,
        0x06, 0x0100, 0,
        descriptor, sizeof descriptor,
        &received, 1000, NULL, &error) ||
      received != sizeof descriptor ||
      descriptor[0] != 18 || descriptor[1] != 1 ||
      descriptor[8] != 0x08 || descriptor[9] != 0x28 ||
      descriptor[10] != 0x55 || descriptor[11] != 0x59)
    {
      if (!error)
        error = fpi_device_error_new (FP_DEVICE_ERROR_PROTO);

      fpi_device_open_complete (dev, g_steal_pointer (&error));
      return;
    }

  g_message ("FT5955 USB descriptor OK: %zu bytes, VID=2808 PID=5955",
             received);
  /* The libfprint core has already opened the USB device. */
  if (!g_usb_device_claim_interface (usb, 0, 0, &error))
    {
      fpi_device_open_complete (dev, g_steal_pointer (&error));
      return;
    }

  /* Audited FocalTech handshake: command 0x34. */
  static const guint8 command[] = {
    0x02, 0x00, 0x01, 0x34, 0x35
  };

  /* Expected 0xAA55 response, plus optional 0x00 trailer. */
  static const guint8 expected[] = {
    0x02, 0x00, 0x03, 0x04, 0x55, 0xaa, 0xf8
  };

  g_autoptr(FpiUsbTransfer) tx = fpi_usb_transfer_new (dev);
  fpi_usb_transfer_fill_bulk (tx, 0x01, sizeof command);
  memcpy (tx->buffer, command, sizeof command);

  if (!fpi_usb_transfer_submit_sync (tx, 1000, &error))
    goto failed;

  if (tx->actual_length != sizeof command)
    {
      error = fpi_device_error_new (FP_DEVICE_ERROR_PROTO);
      goto failed;
    }

  rx = fpi_usb_transfer_new (dev);
  fpi_usb_transfer_fill_bulk (rx, 0x82, 64);

  if (!fpi_usb_transfer_submit_sync (rx, 2000, &error))
    goto failed;

  if (!((rx->actual_length == sizeof expected) ||
        (rx->actual_length == sizeof expected + 1 &&
         rx->buffer[sizeof expected] == 0)) ||
      memcmp (rx->buffer, expected, sizeof expected) != 0)
    {
      error = fpi_device_error_new (FP_DEVICE_ERROR_PROTO);
      goto failed;
    }

  g_message ("FT5955 handshake OK: command 0x34, marker 0xAA55");

  /* Previously validated 0x82 finger-presence request. */
  static const guint8 status_request[] = {
    0x02, 0x00, 0x03, 0x82, 0x73, 0x01, 0xf3
  };

  status_tx = fpi_usb_transfer_new (dev);
  fpi_usb_transfer_fill_bulk (
      status_tx, 0x01, sizeof status_request);
  memcpy (status_tx->buffer, status_request,
          sizeof status_request);

  if (!fpi_usb_transfer_submit_sync (status_tx, 1000, &error))
    goto failed;

  if (status_tx->actual_length != sizeof status_request)
    {
      error = fpi_device_error_new (FP_DEVICE_ERROR_PROTO);
      goto failed;
    }

  status_rx = fpi_usb_transfer_new (dev);
  fpi_usb_transfer_fill_bulk (status_rx, 0x82, 64);

  if (!fpi_usb_transfer_submit_sync (status_rx, 2000, &error))
    goto failed;

  /* Framed response: prefix, length, type, status, XOR.
   * Permit the single observed optional zero trailer. */
  const guint8 *b = status_rx->buffer;
  gssize n = status_rx->actual_length;

  if ((n != 6 && n != 7) ||
      (n == 7 && b[6] != 0) ||
      b[0] != 0x02 ||
      b[1] != 0x00 || b[2] != 0x02 ||
      b[3] != 0x04 ||
      (b[4] != 0x05 && b[4] != 0x06) ||
      b[5] != (b[1] ^ b[2] ^ b[3] ^ b[4]))
    {
      error = fpi_device_error_new (FP_DEVICE_ERROR_PROTO);
      goto failed;
    }

  g_message ("FT5955 finger status: %s",
             b[4] == 0x05 ? "PRESENT" : "ABSENT");

  fpi_device_open_complete (dev, NULL);
  return;

failed:
  g_usb_device_release_interface (usb, 0, 0, NULL);
  fpi_device_open_complete (dev, g_steal_pointer (&error));
}

static void
dev_close (FpDevice *dev)
{
  GError *error = NULL;
  g_usb_device_release_interface (
      fpi_device_get_usb_device (dev), 0, 0, &error);
  fpi_device_close_complete (dev, error);
}

static void
fpi_device_focaltech_5955_init (FpiDeviceFocaltech5955 *self)
{
  (void) self;
}

static void
fpi_device_focaltech_5955_class_init (
    FpiDeviceFocaltech5955Class *klass)
{
  FpDeviceClass *dev_class = FP_DEVICE_CLASS (klass);

  dev_class->id = FP_COMPONENT;
  dev_class->full_name = "FocalTech 5955 (experimental)";
  dev_class->type = FP_DEVICE_TYPE_USB;
  dev_class->id_table = id_table;
  dev_class->scan_type = FP_SCAN_TYPE_PRESS;
  dev_class->nr_enroll_stages = 12;
  dev_class->temp_hot_seconds = -1;
  dev_class->open = dev_open;
  dev_class->close = dev_close;
  dev_class->enroll = ft5955_native_enroll;
  dev_class->verify = ft5955_native_verify;

  fpi_device_class_auto_initialize_features (dev_class);
}
