/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Already audited 2808:5955 packets ONLY: 0x82 status, 0x80 ready, 0x81 image.
 * This module must run in an operation worker, never in libfprint's UI/main loop.
 */
#include "ft5955_native_capture.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

static void zap (void *p, size_t n) {
  volatile uint8_t *v=p; while(n--) *v++=0;
}
static GQuark proto_quark (void) { return g_quark_from_static_string("ft5955-raw-protocol"); }
static gboolean failure (GError **err, const char *msg) {
  g_set_error_literal(err, proto_quark(), 1, msg); return FALSE;
}
static const uint8_t status_cmd[]={0x02,0x00,0x03,0x82,0x73,0x01,0xf3};
static const uint8_t ready_cmd[]={0x02,0x00,0x03,0x80,0x01,0x02,0x80};
static const uint8_t image_cmd[]={0x02,0x00,0x01,0x81,0x80};
static gboolean send_cmd (GUsbDevice *usb, const uint8_t *cmd, size_t n,
                          GCancellable *c, GError **error) {
  gsize got=0;
  if (!g_usb_device_bulk_transfer(usb, 0x01, (guint8 *)cmd,n,&got,1000,c,error)) return FALSE;
  return got==n ? TRUE : failure(error,"Short FT5955 USB command write");
}
static gboolean read_small (GUsbDevice *usb, uint8_t *out, size_t size,
                            size_t *n, GCancellable *c, GError **error) {
  gsize got=0;
  if (!g_usb_device_bulk_transfer(usb,0x82,out,size,&got,2000,c,error)) return FALSE;
  *n=got;return TRUE;
}
/* Validate response frame (02, big-endian len, 04, data..., XOR), and at
 * most a trailing zero. Does not allow shortened packets or silent padding. */
static gboolean small_payload (uint8_t *b, size_t n, size_t bytes, GError **error) {
  const size_t framed=bytes+5;
  if ((n!=framed && !(n==framed+1 && b[framed]==0)) ||
      b[0]!=2 || b[1]!=0 || b[2]!=bytes+1 || b[3]!=4)
    return failure(error,"Invalid FT5955 small frame");
  uint8_t checksum=0;
  for(size_t i=1;i<framed-1;i++)checksum^=b[i];
  return b[framed-1]==checksum ? TRUE : failure(error,"FT5955 small-frame checksum mismatch");
}
static gboolean status (GUsbDevice *usb, GCancellable *c,uint8_t *contact,GError **error) {
  uint8_t reply[64]={0};size_t n=0;
  if (!send_cmd(usb,status_cmd,sizeof status_cmd,c,error) ||
      !read_small(usb,reply,sizeof reply,&n,c,error) ||
      !small_payload(reply,n,1,error))return FALSE;
  *contact=reply[4];
  return (*contact==5 || *contact==6) ? TRUE : failure(error,"Unknown FT5955 finger state");
}
static gboolean ready (GUsbDevice *usb, GCancellable *c,GError **error) {
  uint8_t reply[64]={0};size_t n=0;
  if (!send_cmd(usb,ready_cmd,sizeof ready_cmd,c,error) ||
      !read_small(usb,reply,sizeof reply,&n,c,error) ||
      !small_payload(reply,n,2,error))return FALSE;
  return (reply[4]==0xa5 && reply[5]==0x5a) ? TRUE : failure(error,"FT5955 readiness marker mismatch");
}
static int compare_u16(const void *a,const void *b) {
  uint16_t x=*(const uint16_t *)a,y=*(const uint16_t *)b;return x>y?1:x<y?-1:0;
}
static void convert_pixels (const uint8_t *raw, uint8_t *out) {
  uint16_t sorted[FT5955_PIXELS];
  for(size_t i=0;i<FT5955_PIXELS;i++)sorted[i]=((uint16_t)raw[2*i])|((uint16_t)raw[2*i+1]<<8);
  qsort(sorted,FT5955_PIXELS,sizeof(uint16_t),compare_u16);
  int lo=sorted[(FT5955_PIXELS-1)/100],hi=sorted[((FT5955_PIXELS-1)*99)/100];
  if (hi<=lo) {lo=sorted[0];hi=sorted[FT5955_PIXELS-1];}
  for(size_t i=0;i<FT5955_PIXELS;i++) {
    if(hi<=lo){out[i]=255;continue;}
    int v=(int)((uint16_t)raw[2*i]|((uint16_t)raw[2*i+1]<<8));
    int p=(int)rint((double)(v-lo)*255.0/(hi-lo));
    if (p < 0) p = 0;
    if (p > 255) p = 255;
    out[i]=(uint8_t)(255-p); /* matched MOH WinBio polarity */
  }
  zap(sorted,sizeof sorted);
}
static gboolean read_image (GUsbDevice *usb, GCancellable *c,
                            uint8_t out[FT5955_PIXELS],GError **error) {
  uint8_t wire[10246]={0};size_t count=0;
  if(!send_cmd(usb,image_cmd,sizeof image_cmd,c,error))return FALSE;
  gint64 end=g_get_monotonic_time()+10*G_USEC_PER_SEC;
  gboolean complete=FALSE;
  for(unsigned i=0;i<192 && count<sizeof wire && g_get_monotonic_time()<end;i++) {
    gsize n=0;gsize need=MIN((size_t)64,sizeof(wire)-count);
    if(!g_usb_device_bulk_transfer(usb,0x82,wire+count,need,&n,
                                  count?500:2500,c,error))goto fail;
    if(!n)break;
    count+=n;
    if(count>=3 && wire[0]==2 && (((size_t)wire[1]<<8)|wire[2])==10241) {
      if(count>=10245) {complete=TRUE;break;}
    } else if(count>=10240) {complete=TRUE;break;}
  }
  if(!complete) { failure(error,"Incomplete FT5955 fingerprint frame");goto fail; }
  const uint8_t *raw=NULL;
  if(count==10240)raw=wire; /* same fallback permitted in tested helper */
  else if((count==10245 || count==10246) && wire[0]==2 &&
          wire[1]==0x28 && wire[2]==0x01 && wire[3]==4) {
    uint8_t sum=0;
    for(size_t i=1;i<10244;i++)sum^=wire[i];
    if(sum==wire[10244])raw=wire+4;
  }
  if(!raw){failure(error,"Invalid FT5955 image envelope/checksum");goto fail;}
  convert_pixels(raw,out);
  zap(wire,sizeof wire);
  return TRUE;
fail:
  zap(wire,sizeof wire);
  return FALSE;
}
/* Return one NEW touch only: first observe release, then press. Bounded to
 * 240 polls (two minutes) so a held finger cannot generate more samples. */
gboolean ft5955_native_scan (GUsbDevice *usb, GCancellable *c,
                             uint8_t pixels[FT5955_PIXELS],GError **error) {
  gboolean armed=FALSE;
  for(unsigned poll=0;poll<240;poll++) {
    if(g_cancellable_set_error_if_cancelled(c,error))return FALSE;
    gint64 started=g_get_monotonic_time();
    uint8_t touch;
    if(!status(usb,c,&touch,error))return FALSE;
    if(touch==6)armed=TRUE;
    if(armed && touch==5) {
      g_usleep(10000);
      if(!ready(usb,c,error))return FALSE;
      return read_image(usb,c,pixels,error);
    }
    gint64 pause=500000-(g_get_monotonic_time()-started);
    if(pause>0)g_usleep((gulong)pause);
  }
  return failure(error,"No fresh FT5955 touch within 240 status checks");
}
