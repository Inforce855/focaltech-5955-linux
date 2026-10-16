/* SPDX-License-Identifier: LGPL-2.1-or-later
 * One deliberately explicit, RAM-only libfprint integration test.
 * Does NOT save or export biometric data, install udev rules, or use fprintd.
 */
#include "fprint.h"
#include <glib.h>
#include <stdio.h>
#include <string.h>

static void progress_cb(FpDevice *device,gint accepted,FpPrint *print,
                        gpointer user_data,GError *error) {
  if(error)
    g_print("Scan rejected, reposition finger (accepted %d/12)\n",accepted);
  else
    g_print("Accepted %d/12; LIFT finger fully before next touch\n",accepted);
  (void)device;(void)print;(void)user_data;
}
int main(int argc,char **argv) {
  if(argc!=2 || strcmp(argv[1],"--live")!=0){
    fputs("Explicit --live required. Never run under sudo or through PAM.\n",stderr);return 2;
  }
  if(g_getenv("FT5955_EXPERIMENTAL_ENABLE")==NULL ||
     strcmp(g_getenv("FT5955_EXPERIMENTAL_ENABLE"),"1") ||
     !g_getenv("FT5955_ENGINE_GATEWAY")) {
    fputs("Set FT5955_EXPERIMENTAL_ENABLE=1 and FT5955_ENGINE_GATEWAY.\n",stderr);return 2;
  }
  g_autoptr(FpContext) context=fp_context_new();
  fp_context_enumerate(context);
  GPtrArray *devices=fp_context_get_devices(context);
  FpDevice *device=NULL;
  for(guint i=0;i<devices->len;i++) {
    FpDevice *candidate=g_ptr_array_index(devices,i);
    if(g_strcmp0(fp_device_get_driver(candidate),"focaltech_5955")==0) {
      device=candidate;break;
    }
  }
  if(!device){fputs("Private libfprint did not discover FocalTech 2808:5955.\n",stderr);return 3;}
  g_autoptr(GError) error=NULL;
  if(!fp_device_open_sync(device,NULL,&error)) {
    g_printerr("FT5955 open failed: %s\n",error->message);return 4;
  }
  int result=0;
  g_print("Native private libfprint: 12 accepted impressions; do not switch fingers.\n");
  g_print("No fingerprint images or templates will be written to disk.\n");
  FpPrint *reference=fp_device_enroll_sync(device,fp_print_new(device),NULL,
                                            progress_cb,NULL,&error);
  if(!reference){g_printerr("Enrol stopped: %s\n",error?error->message:"unknown");result=5;goto out;}
  g_print("Enrol complete. Lift and re-touch the enrolled finger to verify.\n");
  gboolean match=FALSE;
  if(!fp_device_verify_sync(device,reference,NULL,NULL,NULL,&match,NULL,&error)) {
    g_printerr("Verify stopped: %s\n",error?error->message:"unknown");result=6;goto cleanup;
  }
  g_print("Fresh verification: %s\n",match?"MATCH":"NO_MATCH");
  g_print("Session complete; print exists in RAM only. No fprintd/PAM modifications.\n");
cleanup:
  g_object_unref(reference);
out:
  g_clear_error(&error);
  if(!fp_device_close_sync(device,NULL,&error))
    g_printerr("FT5955 close: %s\n",error->message);
  return result;
}
