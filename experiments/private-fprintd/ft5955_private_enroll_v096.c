/* SPDX-License-Identifier: MIT
 * FocalTech 5955 v0.9.6: isolated fprintd enrol and verify D-Bus client.
 * No biometric images or templates are read by this client.
 * Run ONLY through the accompanying private-bus launcher.
 */
#include <gio/gio.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define DEST "net.reactivated.Fprint"
#define DEVICE_IFACE "net.reactivated.Fprint.Device"
#define MANAGER_PATH "/net/reactivated/Fprint/Manager"
#define MANAGER_IFACE "net.reactivated.Fprint.Manager"

typedef struct {
    GDBusConnection *bus;
    GMainLoop *loop;
    gchar *path;
    guint sub_id;
    guint timeout_id;
    guint accepted;
    gboolean verifying;
    gboolean finished;
    gboolean succeeded;
    gboolean matched;
    gboolean no_match;
    gboolean claimed;
} Client;

static gboolean private_environment_ok(void)
{
    const gchar *system_bus = g_getenv("DBUS_SYSTEM_BUS_ADDRESS");
    const gchar *session_bus = g_getenv("DBUS_SESSION_BUS_ADDRESS");
    const gchar *storage = g_getenv("STATE_DIRECTORY");
    return geteuid() != 0 && system_bus && *system_bus && session_bus &&
           strcmp(system_bus, session_bus) == 0 && storage &&
           g_str_has_prefix(storage, "/dev/shm/ft5955-v096.") &&
           g_strcmp0(g_getenv("FT5955_V096_PRIVATE_ENROLL"), "1") == 0 &&
           g_strcmp0(g_getenv("FT5955_TEST_PRIVATE_POLKIT"), "1") == 0;
}

static GVariant *invoke(Client *c, const gchar *path, const gchar *iface,
                        const gchar *method, GVariant *params,
                        const GVariantType *reply_type)
{
    g_autoptr(GError) error = NULL;
    GVariant *result = g_dbus_connection_call_sync(
        c->bus, DEST, path, iface, method, params, reply_type,
        G_DBUS_CALL_FLAGS_NO_AUTO_START, 20000, NULL, &error);
    if (!result)
        g_printerr("FAIL: %s: %s\n", method,
                   error ? error->message : "unknown error");
    return result;
}

static gboolean on_timeout(gpointer data)
{
    Client *c = data;
    c->timeout_id = 0;
    g_printerr("FAIL: %s timed out.\n",
               c->verifying ? "Verification" : "Enrolment");
    c->finished = TRUE;
    c->succeeded = FALSE;
    g_main_loop_quit(c->loop);
    return G_SOURCE_REMOVE;
}

static void on_status(GDBusConnection *bus, const gchar *sender,
                      const gchar *object_path, const gchar *interface,
                      const gchar *signal_name, GVariant *parameters,
                      gpointer data)
{
    Client *c = data;
    const gchar *status;
    gboolean done;
    (void)bus; (void)sender; (void)object_path; (void)interface;

    if (c->finished) return;
    if (c->verifying && g_strcmp0(signal_name, "VerifyStatus") != 0) return;
    if (!c->verifying && g_strcmp0(signal_name, "EnrollStatus") != 0) return;

    g_variant_get(parameters, "(&sb)", &status, &done);
    if (!c->verifying && g_strcmp0(status, "enroll-stage-passed") == 0) {
        ++c->accepted;
        g_print("Accepted impression %u. Lift finger fully before next touch.\n",
                c->accepted);
    } else {
        g_print("%s: %s (done=%s)\n", c->verifying ? "Verify" : "Enrol",
                status, done ? "true" : "false");
    }
    fflush(stdout);
    if (done) {
        c->finished = TRUE;
        if (c->verifying) {
            c->matched = g_strcmp0(status, "verify-match") == 0;
            c->no_match = g_strcmp0(status, "verify-no-match") == 0;
            /* Only a terminal match or no-match is a valid comparison result.
             * Quality retries and transport errors must never count as passes. */
            c->succeeded = c->matched || c->no_match;
        } else {
            c->succeeded = g_strcmp0(status, "enroll-completed") == 0;
        }
        g_main_loop_quit(c->loop);
    }
}

static gboolean perform(Client *c, gboolean verify)
{
    const gchar *start = verify ? "VerifyStart" : "EnrollStart";
    const gchar *stop = verify ? "VerifyStop" : "EnrollStop";
    c->verifying = verify;
    c->finished = FALSE;
    c->succeeded = FALSE;
    c->matched = FALSE;
    c->no_match = FALSE;
    c->accepted = 0;
    c->timeout_id = g_timeout_add_seconds(verify ? 90 : 360, on_timeout, c);

    g_autoptr(GVariant) reply = invoke(
        c, c->path, DEVICE_IFACE, start,
        g_variant_new("(s)", "right-index-finger"), G_VARIANT_TYPE("()"));
    if (!reply) {
        if (c->timeout_id) g_source_remove(c->timeout_id);
        c->timeout_id = 0;
        return FALSE;
    }
    g_print("%s started.\n", verify ? "Verification" : "Enrolment");
    fflush(stdout);
    if (!c->finished) g_main_loop_run(c->loop);
    if (c->timeout_id) g_source_remove(c->timeout_id);
    c->timeout_id = 0;

    g_autoptr(GVariant) stopped = invoke(
        c, c->path, DEVICE_IFACE, stop, NULL, G_VARIANT_TYPE("()"));
    return c->succeeded && stopped != NULL;
}

/* Each comparison gets one freshly selected finger. Do not use stdin because
 * a surrounding shell heredoc might have exhausted it. Never auto-scan a finger
 * left resting on the sensor after the preceding comparison. */
static gboolean confirm_finger(const gchar *finger, guint index, guint count)
{
    g_print("\nVerification %u/%u — %s.\n", index, count, finger);
    g_print("Lift any finger OFF the sensor, then press ENTER. "
            "Touch the requested finger only after Verification started.\n");
    fflush(stdout);

    FILE *tty = fopen("/dev/tty", "r");
    if (!tty) {
        g_printerr("STOP: no interactive terminal for verification.\n");
        return FALSE;
    }
    int ch = fgetc(tty);
    fclose(tty);
    if (ch != '\n') {
        g_printerr("STOP: verification requires a fresh ENTER keypress.\n");
        return FALSE;
    }
    return TRUE;
}

static gboolean compare_finger(Client *c, const gchar *finger,
                               gboolean expect_match, guint index, guint count)
{
    if (!confirm_finger(finger, index, count))
        return FALSE;

    if (!perform(c, TRUE)) {
        g_printerr("FAIL: no terminal match/no-match result for %s.\n", finger);
        return FALSE;
    }

    if (c->matched != expect_match) {
        if (c->matched)
            g_printerr("FAIL: UNEXPECTED MATCH on the unenrolled finger (%s). "
                       "Aborting controls.\n", finger);
        else
            g_printerr("FAIL: enrolled finger was NOT recognised (%s). "
                       "Aborting controls.\n", finger);
        return FALSE;
    }
    if (c->matched)
        g_print("PASS: enrolled finger MATCHED (%s).\n", finger);
    else
        g_print("PASS: different finger REJECTED with verify-no-match (%s).\n",
                finger);
    return TRUE;
}

int main(int argc, char **argv)
{
    if (argc != 2 ||
        (g_strcmp0(argv[1], "--live") != 0 &&
         g_strcmp0(argv[1], "--controls") != 0) ||
        !private_environment_ok()) {
        g_printerr("STOP: requires --live or --controls, non-root user, "
                   "private D-Bus and RAM-backed STATE_DIRECTORY "
                   "from v0.9.6 launcher.\n");
        return 2;
    }
    const gboolean controls = g_strcmp0(argv[1], "--controls") == 0;

    Client c = {0};
    int result = 1;
    g_autoptr(GError) error = NULL;
    c.bus = g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, &error);
    if (!c.bus) {
        g_printerr("FAIL: private D-Bus: %s\n", error->message);
        return 3;
    }
    c.loop = g_main_loop_new(NULL, FALSE);
    g_autoptr(GVariant) devices = NULL;
    g_autoptr(GVariant) array = NULL;
    g_autoptr(GVariant) pathv = NULL;
    g_autoptr(GVariant) claim = NULL;

    devices = invoke(&c, MANAGER_PATH, MANAGER_IFACE,
                     "GetDevices", NULL, G_VARIANT_TYPE("(ao)"));
    if (!devices) goto out;
    array = g_variant_get_child_value(devices, 0);
    if (g_variant_n_children(array) != 1) {
        g_printerr("STOP: expected exactly one private-bus fingerprint device.\n");
        goto out;
    }
    pathv = g_variant_get_child_value(array, 0);
    c.path = g_strdup(g_variant_get_string(pathv, NULL));
    g_print("Private device: %s\n", c.path);

    claim = invoke(&c, c.path, DEVICE_IFACE,
                   "Claim", g_variant_new("(s)", ""), G_VARIANT_TYPE("()"));
    if (!claim) goto out;
    c.claimed = TRUE;
    g_print("PASS: Claim succeeded.\n");

    c.sub_id = g_dbus_connection_signal_subscribe(
        c.bus, DEST, DEVICE_IFACE, NULL, c.path, NULL,
        G_DBUS_SIGNAL_FLAGS_NONE, on_status, &c, NULL);

    g_print("Enrolling right-index-finger; use the SAME finger each time.\n");
    fflush(stdout);
    if (!perform(&c, FALSE)) {
        g_printerr("FAIL: enrolment did not finish successfully.\n");
        goto out;
    }
    g_print("PASS: enrolment completed.\n");
    if (!controls) {
        if (!compare_finger(&c, "ENROLLED right index finger", TRUE, 1, 1))
            goto out;
        g_print("PASS: fresh verification MATCH through private fprintd.\n");
    } else {
        /* The VerifyStart record is always right-index-finger; the tester must
         * physically use the displayed finger for each controlled comparison.
         * Negative controls must produce verify-no-match, not a quality error. */
        if (!compare_finger(&c, "ENROLLED right index finger", TRUE, 1, 4))
            goto out;
        if (!compare_finger(&c, "DIFFERENT right middle finger", FALSE, 2, 4))
            goto out;
        if (!compare_finger(&c, "DIFFERENT left index finger", FALSE, 3, 4))
            goto out;
        if (!compare_finger(&c, "ENROLLED right index finger again", TRUE, 4, 4))
            goto out;
        g_print("PASS: controls completed (2 genuine matches, "
                "2 different-finger rejections).\n");
    }
    result = 0;

out:
    if (c.sub_id) g_dbus_connection_signal_unsubscribe(c.bus, c.sub_id);
    if (c.claimed) {
        g_autoptr(GVariant) release = invoke(
            &c, c.path, DEVICE_IFACE, "Release", NULL, G_VARIANT_TYPE("()"));
        if (!release) result = 1;
    }
    g_free(c.path);
    g_main_loop_unref(c.loop);
    g_object_unref(c.bus);
    return result;
}
