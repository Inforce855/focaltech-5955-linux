/* SPDX-License-Identifier: MIT
 * v0.9.7: single-purpose private-bus discovery / Claim / Release probe.
 *
 * NO EnrollStart, VerifyStart, ListEnrolledFingers, image or template access.
 * It must be run through a disposable non-root private D-Bus launcher.
 */
#include <gio/gio.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define FPRINT "net.reactivated.Fprint"
#define MANAGER "/net/reactivated/Fprint/Manager"
#define MANAGER_IFACE "net.reactivated.Fprint.Manager"
#define DEVICE_IFACE "net.reactivated.Fprint.Device"

static gboolean
private_bus_ok (void)
{
  const char *system = g_getenv ("DBUS_SYSTEM_BUS_ADDRESS");
  const char *session = g_getenv ("DBUS_SESSION_BUS_ADDRESS");
  const char *storage = g_getenv ("STATE_DIRECTORY");
  return geteuid () != 0 &&
         system && session && *system &&
         g_strcmp0 (system, session) == 0 &&
         storage && g_str_has_prefix (storage, "/dev/shm/ft5955-claim-only.") &&
         g_strcmp0 (g_getenv ("FT5955_TEST_PRIVATE_POLKIT"), "1") == 0 &&
         g_strcmp0 (g_getenv ("FT5955_CLAIM_ONLY"), "1") == 0;
}

static GVariant *
invoke (GDBusConnection *bus, const char *path, const char *interface,
        const char *method, GVariant *args, const GVariantType *type)
{
  g_autoptr(GError) error = NULL;
  GVariant *reply = g_dbus_connection_call_sync (
      bus, FPRINT, path, interface, method, args, type,
      G_DBUS_CALL_FLAGS_NO_AUTO_START, 20000, NULL, &error);
  if (!reply)
    g_printerr ("FAIL: %s: %s\n", method,
                error ? error->message : "unknown D-Bus error");
  return reply;
}

int
main (int argc, char **argv)
{
  if (argc != 2 || strcmp (argv[1], "--claim-only") != 0 ||
      !private_bus_ok ())
    {
      g_printerr ("STOP: Claim-only probe requires private D-Bus, "
                  "isolated RAM state, non-root and explicit test flags.\n");
      return 2;
    }

  g_autoptr(GError) error = NULL;
  g_autoptr(GDBusConnection) bus =
      g_bus_get_sync (G_BUS_TYPE_SYSTEM, NULL, &error);
  if (!bus)
    {
      g_printerr ("FAIL: private bus: %s\n", error->message);
      return 3;
    }

  g_autoptr(GVariant) devices = invoke (
      bus, MANAGER, MANAGER_IFACE, "GetDevices",
      NULL, G_VARIANT_TYPE ("(ao)"));
  if (!devices)
    return 4;

  g_autoptr(GVariant) paths = g_variant_get_child_value (devices, 0);
  if (g_variant_n_children (paths) != 1)
    {
      g_printerr ("FAIL: expected exactly one private fingerprint device; found %zu.\n",
                  g_variant_n_children (paths));
      return 4;
    }

  g_autoptr(GVariant) item = g_variant_get_child_value (paths, 0);
  const char *path = g_variant_get_string (item, NULL);
  g_print ("PASS: discovered one private device: %s\n", path);
  fflush (stdout);

  g_autoptr(GVariant) claim = invoke (
      bus, path, DEVICE_IFACE, "Claim",
      g_variant_new ("(s)", ""), G_VARIANT_TYPE ("()"));
  if (!claim)
    return 5;
  g_print ("PASS: Claim succeeded using rebuilt GitHub library.\n");
  fflush (stdout);

  g_autoptr(GVariant) release = invoke (
      bus, path, DEVICE_IFACE, "Release", NULL, G_VARIANT_TYPE ("()"));
  if (!release)
    {
      g_printerr ("FAIL: Release failed after Claim; private fprintd "
                  "will be stopped by the launcher.\n");
      return 6;
    }
  g_print ("PASS: Release succeeded.\n"
           "PASS: NO EnrollStart, VerifyStart or biometric capture requested.\n");
  return 0;
}
