/* SPDX-License-Identifier: MIT
 * FT5955 v0.9.5 — disposable PRIVATE-BUS PolicyKit protocol stub.
 * Never run as root or on the real system bus.
 * For Claim, Enroll and Verify testing only.
 */
#include <gio/gio.h>
#include <glib.h>
#include <string.h>
#include <unistd.h>

static const gchar xml[] =
"<node><interface name='org.freedesktop.PolicyKit1.Authority'>"
"<method name='CheckAuthorization'>"
"<arg type='(sa{sv})' direction='in'/>"
"<arg type='s' direction='in'/>"
"<arg type='a{ss}' direction='in'/>"
"<arg type='u' direction='in'/>"
"<arg type='s' direction='in'/>"
"<arg type='(bba{ss})' direction='out'/>"
"</method>"
"<property name='BackendName' type='s' access='read'/>"
"<property name='BackendVersion' type='s' access='read'/>"
"<property name='BackendFeatures' type='u' access='read'/>"
"</interface></node>";

static gboolean is_local_bus_user(GDBusConnection *bus, const gchar *unique_name)
{
    if (!unique_name || !g_dbus_is_unique_name(unique_name))
        return FALSE;
    g_autoptr(GError) error = NULL;
    g_autoptr(GVariant) value = g_dbus_connection_call_sync(
        bus, "org.freedesktop.DBus", "/org/freedesktop/DBus",
        "org.freedesktop.DBus", "GetConnectionUnixUser",
        g_variant_new("(s)", unique_name), G_VARIANT_TYPE("(u)"),
        G_DBUS_CALL_FLAGS_NONE, 2000, NULL, &error);
    if (!value)
        return FALSE;
    guint32 uid = G_MAXUINT32;
    g_variant_get(value, "(u)", &uid);
    return uid == (guint32)getuid();
}

static void method_call(GDBusConnection *bus, const gchar *sender,
                        const gchar *object_path, const gchar *interface_name,
                        const gchar *method_name, GVariant *parameters,
                        GDBusMethodInvocation *invocation, gpointer user_data)
{
    (void)object_path; (void)interface_name; (void)user_data;
    if (g_strcmp0(method_name, "CheckAuthorization") != 0) {
        g_dbus_method_invocation_return_dbus_error(
            invocation, "org.freedesktop.DBus.Error.UnknownMethod",
            "Private test stub only implements CheckAuthorization");
        return;
    }

    g_autoptr(GVariant) subject = g_variant_get_child_value(parameters, 0);
    g_autoptr(GVariant) kind = g_variant_get_child_value(subject, 0);
    g_autoptr(GVariant) details = g_variant_get_child_value(subject, 1);
    g_autoptr(GVariant) action_variant = g_variant_get_child_value(parameters, 1);
    const gchar *action = g_variant_get_string(action_variant, NULL);
    const gchar *subject_kind = g_variant_get_string(kind, NULL);
    g_autoptr(GVariant) name = g_variant_lookup_value(
        details, "name", G_VARIANT_TYPE_STRING);
    const gchar *target = name ? g_variant_get_string(name, NULL) : NULL;

    gboolean action_ok =
        g_strcmp0(action, "net.reactivated.fprint.device.enroll") == 0 ||
        g_strcmp0(action, "net.reactivated.fprint.device.verify") == 0;
    gboolean allow = action_ok &&
        g_strcmp0(subject_kind, "system-bus-name") == 0 &&
        is_local_bus_user(bus, sender) &&
        is_local_bus_user(bus, target);

    GVariantBuilder builder;
    g_variant_builder_init(&builder, G_VARIANT_TYPE("a{ss}"));
    g_dbus_method_invocation_return_value(invocation,
        g_variant_new("(@(bba{ss}))",
            g_variant_new("(bb@a{ss})", allow, FALSE,
                          g_variant_builder_end(&builder))));
    g_print("PRIVATE BUS TEST PolicyKit: action=%s decision=%s\n",
            action, allow ? "ALLOW" : "DENY");
}

static GVariant *get_property(GDBusConnection *connection,
                              const gchar *sender, const gchar *object_path,
                              const gchar *interface_name,
                              const gchar *property_name, GError **error,
                              gpointer user_data)
{
    (void)connection; (void)sender; (void)object_path;
    (void)interface_name; (void)user_data;
    if (g_strcmp0(property_name, "BackendName") == 0)
        return g_variant_new_string("FT5955 private-bus test only");
    if (g_strcmp0(property_name, "BackendVersion") == 0)
        return g_variant_new_string("0.9.5");
    if (g_strcmp0(property_name, "BackendFeatures") == 0)
        return g_variant_new_uint32(0);
    g_set_error(error, G_IO_ERROR, G_IO_ERROR_NOT_SUPPORTED,
                "Unknown test property %s", property_name);
    return NULL;
}

static const GDBusInterfaceVTable vtable =
    { method_call, get_property, NULL, {0} };

static void name_acquired(GDBusConnection *bus, const gchar *name, gpointer data)
{
    (void)bus; (void)data;
    g_print("PRIVATE BUS TEST PolicyKit name acquired: %s\n", name);
}

static void name_lost(GDBusConnection *bus, const gchar *name, gpointer data)
{
    (void)bus; (void)data;
    g_printerr("FAIL: test PolicyKit bus name lost: %s\n", name);
    _exit(3);
}

int main(void)
{
    const gchar *system = g_getenv("DBUS_SYSTEM_BUS_ADDRESS");
    const gchar *session = g_getenv("DBUS_SESSION_BUS_ADDRESS");
    if (geteuid() == 0 || !system || !session || !*system ||
        g_strcmp0(system, session) != 0 ||
        g_strcmp0(g_getenv("FT5955_TEST_PRIVATE_POLKIT"), "1") != 0 ||
        !g_getenv("STATE_DIRECTORY")) {
        g_printerr("STOP: requires disposable private D-Bus, "
                   "non-root user and temporary storage.\n");
        return 2;
    }
    g_autoptr(GError) error = NULL;
    g_autoptr(GDBusNodeInfo) info = g_dbus_node_info_new_for_xml(xml, &error);
    if (!info) {
        g_printerr("Invalid PolicyKit XML: %s\n", error->message);
        return 2;
    }
    g_autoptr(GDBusConnection) bus =
        g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, &error);
    if (!bus) {
        g_printerr("Private bus unavailable: %s\n", error->message);
        return 2;
    }
    guint registration = g_dbus_connection_register_object(
        bus, "/org/freedesktop/PolicyKit1/Authority", info->interfaces[0],
        &vtable, NULL, NULL, &error);
    if (!registration) {
        g_printerr("PolicyKit test registration failed: %s\n", error->message);
        return 2;
    }
    guint owner = g_bus_own_name_on_connection(
        bus, "org.freedesktop.PolicyKit1", G_BUS_NAME_OWNER_FLAGS_NONE,
        name_acquired, name_lost, NULL, NULL);
    g_autoptr(GMainLoop) loop = g_main_loop_new(NULL, FALSE);
    g_main_loop_run(loop);
    g_bus_unown_name(owner);
    g_dbus_connection_unregister_object(bus, registration);
    return 0;
}
