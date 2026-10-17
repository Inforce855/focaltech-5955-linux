/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Experimental asynchronous FT5955 enrol/verify path.
 * USB capture in a worker; engine runs in independent audited bwrap process.
 * Never call fpi_device_* outside the libfprint main context.
 * Opt-in is required, and NO system authentication stack is modified here.
 */
#define FP_COMPONENT "focaltech_5955"
#include "drivers_api.h"
#include "ft5955_native_action.h"
#include "ft5955_native_capture.h"
#include "ft5955_fpi_action_bridge.h"
#include "ft5955_fpi_print_bridge.h"
#include <glib.h>
#include <gio/gio.h>
#include <stdint.h>
#include <stdio.h>
#include <signal.h>
#include <string.h>

#define MAX_CAPTURES_ENROLL 96
#define MAX_CAPTURES_VERIFY 16
#define MAX_LINE 127

static void sensitive_clear (void *p,size_t len) {
  volatile uint8_t *a=p;while(len--)*a++=0;
}

typedef struct {
  gboolean enrolling;
  GUsbDevice *usb;        /* ref held while worker is active */
  GMainContext *context; /* creator's libfprint context */
  Ft5955Action action;   /* main-context only */
  Ft5955PrintTemplate candidate; /* verify data copied on main context */
  guint8 *new_template;
  size_t new_template_len;
  guint8 new_subfactor;
  gboolean pending;
  GError *worker_error;
} FtJob;

typedef struct {
  FpDevice *device;
  FtJob *job;
  gchar *line;
} Progress;

static gboolean progress_on_main (gpointer payload) {
  Progress *p=payload;
  /* fpi_device_* callbacks always run on the captured main context. */
  ft5955_fpi_apply_reply(p->device,&p->job->action,p->line,NULL,0,0);
  return G_SOURCE_REMOVE;
}
static void progress_free (gpointer payload) {
  Progress *p=payload;
  g_object_unref(p->device);g_free(p->line);g_free(p);
}
static void post_progress (GTask *task,FtJob *job,const gchar *line) {
  Progress *p=g_new0(Progress,1);
  p->device=g_object_ref(g_task_get_source_object(task));
  p->job=job;
  p->line=g_strdup(line);
  GSource *source=g_idle_source_new();
  g_source_set_priority(source,G_PRIORITY_HIGH); /* run before GTask finish */
  g_source_set_callback(source,progress_on_main,p,progress_free);
  g_source_attach(source,job->context);
  g_source_unref(source);
}
static void job_free (gpointer data) {
  FtJob *j=data;
  ft5955_print_template_clear(&j->candidate);
  if(j->new_template)ft5955_free_sensitive(j->new_template,j->new_template_len);
  g_clear_object(&j->usb);
  g_main_context_unref(j->context);
  g_clear_error(&j->worker_error);
  g_free(j);
}

static gboolean write_all (GOutputStream *out,const void *ptr,size_t size,
                           GCancellable *c,GError **err) {
  gsize written=0;
  return g_output_stream_write_all(out,ptr,size,&written,c,err)&&written==size;
}
static gchar *read_line (GDataInputStream *in,GCancellable *c,GError **err) {
  char line[MAX_LINE+1]={0};
  for(size_t length=0;length<MAX_LINE;length++) {
    unsigned char b=0;
    gssize n=g_input_stream_read(G_INPUT_STREAM(in),&b,1,c,err);
    if(n<0)return NULL;
    if(n==0){g_set_error_literal(err,G_IO_ERROR,G_IO_ERROR_PARTIAL_INPUT,
                                  "Unexpected end of MOH reply");return NULL;}
    if(b=='\n')return g_strndup(line,length);
    if(b<32 || b>126){g_set_error_literal(err,G_IO_ERROR,G_IO_ERROR_INVALID_DATA,
                                        "Invalid MOH reply character");return NULL;}
    line[length]=(char)b;
  }
  g_set_error_literal(err,G_IO_ERROR,G_IO_ERROR_INVALID_DATA,"Oversized MOH reply");
  return NULL;
}
static gboolean read_all (GInputStream *in,void *dst,size_t size,GCancellable *c,GError **err) {
  gsize done=0;
  if(!g_input_stream_read_all(in,dst,size,&done,c,err))return FALSE;
  if(done!=size){g_set_error_literal(err,G_IO_ERROR,G_IO_ERROR_PARTIAL_INPUT,"Truncated MOH template");return FALSE;}
  return TRUE;
}
static gboolean start_gateway (FtJob *job,GSubprocess **proc,
                               GInputStream **input,GOutputStream **output,
                               GCancellable *c,GError **err) {
  const char *script=g_getenv("FT5955_ENGINE_GATEWAY");
  if(!script || !g_path_is_absolute(script) || !g_file_test(script,G_FILE_TEST_IS_REGULAR)) {
    g_set_error_literal(err,G_IO_ERROR,G_IO_ERROR_NOT_SUPPORTED,
      "Set FT5955_ENGINE_GATEWAY to the absolute path of the audited experimental engine_gateway.py");
    return FALSE;
  }
  *proc=g_subprocess_new(G_SUBPROCESS_FLAGS_STDIN_PIPE | G_SUBPROCESS_FLAGS_STDOUT_PIPE |
                           G_SUBPROCESS_FLAGS_STDERR_SILENCE,
                          err,"/usr/bin/python3",script,NULL);
  if(!*proc)return FALSE;
  *output=g_subprocess_get_stdin_pipe(*proc);
  *input=G_INPUT_STREAM(g_data_input_stream_new(g_subprocess_get_stdout_pipe(*proc)));
  (void)job;(void)c;
  return TRUE;
}
static gboolean startup (FtJob *job,GInputStream *in,GOutputStream *out,
                         GCancellable *c,GError **err) {
  gchar *line=NULL;
  gboolean good=FALSE;
  if(job->enrolling) {
    if(!write_all(out,"MODE E\n",7,c,err))return FALSE;
  } else {
    g_autofree char *cmd=g_strdup_printf("MODE V %zu %u\n",job->candidate.length,
                                         (unsigned)job->candidate.subfactor);
    if(!write_all(out,cmd,strlen(cmd),c,err) ||
       !write_all(out,job->candidate.bytes,job->candidate.length,c,err))return FALSE;
  }
  line=read_line(G_DATA_INPUT_STREAM(in),c,err);
  if(line){good=strcmp(line,"READY 1")==0;g_free(line);}
  if(!good && !*err)
    g_set_error_literal(err,G_IO_ERROR,G_IO_ERROR_INVALID_DATA,"MOH gateway did not initialise");
  return good;
}
static gboolean parse_template (FtJob *job,GInputStream *in,GCancellable *c,GError **err) {
  g_autofree gchar *header=read_line(G_DATA_INPUT_STREAM(in),c,err);
  unsigned long n=0;unsigned sub=0;char extra=0;
  if(!header || sscanf(header,"TEMPLATE %lu %u%c",&n,&sub,&extra)!=2 ||
     n<1 || n>FT5955_PRINT_MAX_TEMPLATE || sub>255) {
    if(!*err)g_set_error_literal(err,G_IO_ERROR,G_IO_ERROR_INVALID_DATA,"Invalid MOH export header");
    return FALSE;
  }
  job->new_template=g_malloc(n);
  job->new_template_len=n;
  job->new_subfactor=(guint8)sub;
  return read_all(in,job->new_template,n,c,err);
}
static void worker (GTask *task,gpointer source,gpointer user,GCancellable *c) {
  FtJob *job=user;
  GError *err=NULL;
  GSubprocess *child=NULL;
  GInputStream *in=NULL;
  GOutputStream *out=NULL;
  guint8 frame[FT5955_PIXELS]={0};
  gboolean done=FALSE;
  Ft5955Action guard;
  ft5955_action_begin(&guard,job->enrolling?FT5955_ACTION_ENROLL:FT5955_ACTION_VERIFY);
  unsigned max=job->enrolling?MAX_CAPTURES_ENROLL:MAX_CAPTURES_VERIFY;
  if(!start_gateway(job,&child,&in,&out,c,&err) || !startup(job,in,out,c,&err))goto end;
  for(unsigned i=0;i<max;i++) {
    if(!ft5955_native_scan(job->usb,c,frame,&err))goto end;
    if(!write_all(out,"FRAME\n",6,c,&err) ||
       !write_all(out,frame,sizeof frame,c,&err))goto end;
    sensitive_clear(frame,sizeof frame);
    g_autofree gchar *reply=read_line(G_DATA_INPUT_STREAM(in),c,&err);
    if(!reply)goto end;
    unsigned stage=0;
    Ft5955DriverEvent event=ft5955_action_consume_reply(&guard,reply,&stage);
    if(event==FT5955_DRIVER_PROGRESS || event==FT5955_DRIVER_RETRY) {
      post_progress(task,job,reply);
      continue;
    }
    if(job->enrolling && event==FT5955_DRIVER_ENROLLED) {
      if(!parse_template(job,in,c,&err))goto end;
      done=TRUE;break;
    }
    if(!job->enrolling && (event==FT5955_DRIVER_MATCHED ||
                            event==FT5955_DRIVER_NOT_MATCHED)) {
      job->pending=event==FT5955_DRIVER_MATCHED;
      done=TRUE;break;
    }
    g_set_error_literal(&err,G_IO_ERROR,G_IO_ERROR_INVALID_DATA,
                        "Invalid MOH reply or enrolment stage order");
    goto end;
  }
  if(!done)g_set_error_literal(&err,G_IO_ERROR,G_IO_ERROR_TIMED_OUT,"FT5955 capture attempt limit reached");
end:
  sensitive_clear(frame,sizeof frame);
  if(child) {
    /* QUIT lets the supervised Python gateway close the bwrap engine and wipe
     * its template. The worker does not rely on main-loop timers here. */
    if(out && !(g_subprocess_get_identifier(child) == NULL)) {
      gsize ignored=0;
      (void)g_output_stream_write_all(out,"QUIT\n",5,&ignored,NULL,NULL);
    }
    gint64 limit=g_get_monotonic_time()+10*G_USEC_PER_SEC;
    while(!(g_subprocess_get_identifier(child) == NULL) && g_get_monotonic_time()<limit)
      g_usleep(20000);
    if(!(g_subprocess_get_identifier(child) == NULL)) {
      g_subprocess_send_signal(child,SIGTERM); /* Python's cleanup handler */
      limit=g_get_monotonic_time()+3*G_USEC_PER_SEC;
      while(!(g_subprocess_get_identifier(child) == NULL) && g_get_monotonic_time()<limit)
        g_usleep(20000);
    }
    if(!(g_subprocess_get_identifier(child) == NULL))g_subprocess_force_exit(child);
    g_subprocess_wait(child,NULL,NULL);
    g_object_unref(child);
  }
  if(in)g_object_unref(in);
  if(err)g_task_return_error(task,err);
  else g_task_return_boolean(task,TRUE);
  (void)source;
}
static void finish (GObject *source,GAsyncResult *res,gpointer unused) {
  FpDevice *dev=FP_DEVICE(source);
  GTask *task=G_TASK(res);
  FtJob *job=g_task_get_task_data(task);
  g_autoptr(GError) err=NULL;
  gboolean ok=g_task_propagate_boolean(task,&err);
  if(job->enrolling) {
    if(!ok)fpi_device_enroll_complete(dev,NULL,g_steal_pointer(&err));
    else ft5955_fpi_apply_reply(dev,&job->action,"COMPLETE",
                               job->new_template,job->new_template_len,job->new_subfactor);
  } else {
    if(!ok)fpi_device_verify_complete(dev,g_steal_pointer(&err));
    else ft5955_fpi_apply_reply(dev,&job->action,
                                job->pending?"MATCH":"NO_MATCH",NULL,0,0);
  }
  (void)unused;
}
static void launch (FpDevice *device,gboolean enrolling) {
  GError *err=NULL;
  if(g_strcmp0(g_getenv("FT5955_EXPERIMENTAL_ENABLE"),"1")!=0) {
    err=fpi_device_error_new_msg(FP_DEVICE_ERROR_NOT_SUPPORTED,
             "FT5955 experimental biometric operations are disabled");
    goto fail;
  }
  FtJob *job=g_new0(FtJob,1);
  job->enrolling=enrolling;
  job->usb=g_object_ref(fpi_device_get_usb_device(device));
  job->context=g_main_context_ref_thread_default();
  ft5955_action_begin(&job->action,enrolling?FT5955_ACTION_ENROLL:FT5955_ACTION_VERIFY);
  if(!enrolling) {
    FpPrint *print=NULL;
    fpi_device_get_verify_data(device,&print);
    if(!print || !ft5955_fpprint_extract(print,&job->candidate)) {
      err=fpi_device_error_new_msg(FP_DEVICE_ERROR_DATA_INVALID,"FT5955 template invalid or incompatible");
      job_free(job);
      goto fail;
    }
  }
  GTask *task=g_task_new(device,fpi_device_get_cancellable(device),finish,NULL);
  g_task_set_task_data(task,job,job_free);
  g_task_set_return_on_cancel(task,FALSE);
  g_task_run_in_thread(task,worker);
  g_object_unref(task);
  return;
fail:
  if(enrolling)fpi_device_enroll_complete(device,NULL,err);
  else fpi_device_verify_complete(device,err);
}
void ft5955_native_enroll(FpDevice *dev) { launch(dev,TRUE); }
void ft5955_native_verify(FpDevice *dev) { launch(dev,FALSE); }
