/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Multi-sample P5 PGM enrolment diagnostic for the isolated 5955 MOH engine.
 * Calls CreateEnrollment and UpdateEnrollment; does not commit a template. Never prints pixels.
 */
#include "ft_engine.h"
#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MAX_DIM 2048
#define MAX_PIXELS (MAX_DIM*MAX_DIM)
#define BAD_CAPTURE UINT32_C(0x80098008)
#if defined(FT5955_OFFLINE_QUERY_SAMPLE_HINT)
extern void ft_engine_log_sample_hint(void);
#endif
#if defined(FT5955_OFFLINE_PROBE_COMMIT)
extern int ft_engine_probe_commit_offline(void);
#endif
#if defined(FT5955_OFFLINE_VERIFY_AFTER_COMMIT)
extern void ft_engine_probe_verify_current_offline(int index);
extern void ft_engine_probe_wipe_offline(void);
#endif
#if defined(FT5955_OFFLINE_PROBE_DUPLICATE)
extern int ft_engine_probe_duplicate_offline(void);
#endif
#if defined(FT5955_OFFLINE_QUERY_EXTENDED_ENROLLMENT_STATUS)
extern void ft_engine_log_extended_enrollment_status(void);
#endif


#if defined(FT5955_OFFLINE_WINDOWS_BIR_DIRECT)
extern uint32_t ft_engine_accept_offline_windows_bir(
    const uint8_t *bir,size_t length,uint8_t purpose);
#endif

/* Only the already-observed Focal5955 Windows Raw BIR layout is allowed.
 * This validator intentionally does not attempt to parse arbitrary WinBio
 * records or export any bytes outside the disposable sandbox. */
#if defined(FT5955_OFFLINE_WINDOWS_BIR_DIRECT) || defined(FT5955_OFFLINE_WINDOWS_BIR_SYNTHETIC)
#define WIN_BIR_SIZE 5256u
#define WIN_BIR_PIXEL_OFFSET 136u
#define WIN_BIR_PIXEL_SIZE 5120u
static uint32_t read32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8)
        | ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static uint8_t *read_windows_bir(const char *path)
{
    FILE *fp=fopen(path,"rb");
    if(!fp){ perror("[5955] Windows BIR open");return NULL; }
    uint8_t *buf=malloc(WIN_BIR_SIZE);
    if(!buf){ fclose(fp);return NULL; }
    int ok=fread(buf,1,WIN_BIR_SIZE,fp)==WIN_BIR_SIZE
        && fgetc(fp)==EOF && !ferror(fp);
    fclose(fp);
    const uint32_t expected[]={
        48,32, 40,80, 5136,120, 0,0
    };
    if(ok) {
        for(size_t k=0;k<8;k++) {
            if(read32(buf+k*4)!=expected[k]) ok=0;
        }
    }
    if(ok && (buf[32+4]&0x02)) ok=0; /* Encrypted-record flag */
    if(!ok) {
        fprintf(stderr,"[5955] Windows BIR rejected: unexpected size, "
                "layout or encrypted data. No data displayed.\n");
        memset(buf,0,WIN_BIR_SIZE);free(buf);
        return NULL;
    }
    return buf;
}
#endif

static int token(FILE *fp, char *out, size_t cap)
{
    int c;
    do {
        c=fgetc(fp);
        if(c=='#') { while((c=fgetc(fp))!=EOF && c!='\n'){} }
    } while(c!=EOF && isspace((unsigned char)c));
    if(c==EOF) return 0;
    size_t n=0;
    do {
        if(n+1>=cap) return 0;
        out[n++]=(char)c;
        c=fgetc(fp);
    } while(c!=EOF && !isspace((unsigned char)c) && c!='#');
    if(c=='#') { while((c=fgetc(fp))!=EOF && c!='\n'){} }
    out[n]=0;
    /* Important: exactly one separator after maxval; do not consume pixel
     * bytes (which themselves may resemble whitespace or '#'). */
    return n!=0;
}
static int decimal(const char *s, unsigned *value)
{
    if(!*s) return 0;
    unsigned v=0;
    for(;*s;s++) {
        if(*s<'0'||*s>'9') return 0;
        unsigned digit=(unsigned)(*s-'0');
        if(v>(UINT32_MAX-digit)/10u) return 0;
        v=v*10u+digit;
    }
    *value=v;
    return 1;
}
static uint8_t *read_pgm(const char *path,unsigned *w,unsigned *h)
{
    FILE *fp=fopen(path,"rb");
    if(!fp) { perror("[5955] PGM open"); return NULL; }
    char t[80];
    unsigned maxval=0;
    if(!token(fp,t,sizeof t)||strcmp(t,"P5")||
       !token(fp,t,sizeof t)||!decimal(t,w)||
       !token(fp,t,sizeof t)||!decimal(t,h)||
       !token(fp,t,sizeof t)||!decimal(t,&maxval)||
       *w==0||*w>MAX_DIM||*h==0||*h>MAX_DIM||maxval!=255) {
        fprintf(stderr,"[5955] PGM rejected: need binary P5, 8-bit maxval 255, dimensions 1..2048\n");
        fclose(fp);return NULL;
    }
    size_t n=(size_t)*w * *h;
    uint8_t *pixels=malloc(n);
    if(!pixels) { fclose(fp);return NULL; }
    if(fread(pixels,1,n,fp)!=n || fgetc(fp)!=EOF || ferror(fp)) {
        fprintf(stderr,"[5955] PGM rejected: truncated or trailing bytes\n");
        free(pixels);fclose(fp);return NULL;
    }
    fclose(fp);
    return pixels;
}
int main(int argc,char **argv)
{
    if(argc<4 || argc>23 || strcmp(argv[1],"--pgm-enroll-batch")!=0){
        fprintf(stderr,"Usage: %s --pgm-enroll-batch /tmp/engine.dll sample1.pgm sample2.pgm [...]\\n",argv[0]);
        return 2;
    }
    int status=ft_engine_open(argv[2]);
    fprintf(stderr,"[5955] Attach wrapper status: %d\\n",status);
    if(status!=0) return 1;
#if defined(FT5955_OFFLINE_QUERY_SAMPLE_HINT)
    ft_engine_log_sample_hint();
#endif
    if(ft_engine_enroll_begin()!=0) {
        fprintf(stderr,"[5955] CreateEnrollment failed; stopping offline replay.\n");
        return 3;
    }
    fprintf(stderr,"[5955] CreateEnrollment initiated; %d distinct-capture files supplied.\\n",argc-3);
    int result=1;
#if defined(FT5955_OFFLINE_VERIFY_AFTER_COMMIT)
    int next_verify=argc;
    int commit_ok=0;
#endif
    for(int i=3;i<argc;i++){
        unsigned w=0,h=0;
        uint32_t hr=UINT32_MAX;
#if defined(FT5955_OFFLINE_WINDOWS_BIR_DIRECT) || defined(FT5955_OFFLINE_WINDOWS_BIR_SYNTHETIC)
        uint8_t *windows_bir=read_windows_bir(argv[i]);
        if(!windows_bir) return 2;
        fprintf(stderr,"[5955] Enrolment sample %d/%d: genuine Windows BIR, 5256 bytes.\n",i-2,argc-3);
#if defined(FT5955_OFFLINE_WINDOWS_BIR_DIRECT)
        fprintf(stderr,"[5955] WINDOWS_BIR_TEST direct-unchanged\n");
        hr=ft_engine_accept_offline_windows_bir(windows_bir,WIN_BIR_SIZE,4);
#else
        fprintf(stderr,"[5955] WINDOWS_BIR_TEST synthetic-from-vendor-pixels\n");
        hr=ft_engine_accept(windows_bir+WIN_BIR_PIXEL_OFFSET,64,80,4);
#endif
        memset(windows_bir,0,WIN_BIR_SIZE);
        free(windows_bir);
#else
        uint8_t *pixels=read_pgm(argv[i],&w,&h);
        if(!pixels) return 2;
        fprintf(stderr,"[5955] Enrolment sample %d/%d: %ux%u P5 image.\\n",i-2,argc-3,w,h);
        if(w!=64 || h!=80) fprintf(stderr,"[5955] WARNING: image will be cropped/scaled to 64x80.\\n");
#if defined(FT5955_OFFLINE_INVERT_INPUT_PIXELS)
        for(size_t j=0;j<(size_t)w*h;j++) pixels[j]=(uint8_t)(255u-pixels[j]);
        fprintf(stderr,"[5955] OFFLINE_INPUT_POLARITY inverted\n");
#else
        fprintf(stderr,"[5955] OFFLINE_INPUT_POLARITY original\n");
#endif
        hr=ft_engine_accept(pixels,(int)w,(int)h,4);
        memset(pixels,0,(size_t)w*h);
        free(pixels);
#endif
        fprintf(stderr,"[5955] AcceptSampleData HRESULT: 0x%08x\\n",hr);
        if(hr==BAD_CAPTURE){
            fprintf(stderr,"[5955] Rejected image; proceeding to next distinct capture.\\n");
            continue;
        }
        if(hr!=0){
            fprintf(stderr,"[5955] Unexpected HRESULT; stopping.\\n");
            return 3;
        }
        int update=ft_engine_enroll_update();
#if defined(FT5955_OFFLINE_QUERY_EXTENDED_ENROLLMENT_STATUS)
        ft_engine_log_extended_enrollment_status();
#endif
        fprintf(stderr,"[5955] UpdateEnrollment sample %d: %d (0=complete,1=more,2=rejected).\\n",i-2,update);
        if(update<0 || update>2) return 3;
        if(update==0){
            fprintf(stderr,"[5955] Capture collection reached UpdateEnrollment S_OK.\\n");
#if defined(FT5955_OFFLINE_PROBE_COMMIT)
#if defined(FT5955_OFFLINE_PROBE_DUPLICATE)
            fprintf(stderr,"[5955] DOCUMENTED_COMMIT_WORKFLOW duplicate check before commit.\\n");
            int preflight=ft_engine_probe_duplicate_offline();
            if(preflight==0){
                fprintf(stderr,"[5955] Attempting experimental CommitEnrollment into mock storage ONLY.\\n");
    #if defined(FT5955_OFFLINE_VERIFY_AFTER_COMMIT)
            commit_ok=ft_engine_probe_commit_offline();
            next_verify=i+1;
#else
            ft_engine_probe_commit_offline();
#endif
            } else {
                fprintf(stderr,"[5955] COMMIT_PROBE skipped=duplicate-preflight-blocked.\\n");
            }
#else
            fprintf(stderr,"[5955] Attempting experimental CommitEnrollment into mock storage ONLY.\\n");
#if defined(FT5955_OFFLINE_VERIFY_AFTER_COMMIT)
            commit_ok=ft_engine_probe_commit_offline();
            next_verify=i+1;
#else
            ft_engine_probe_commit_offline();
#endif
#endif
#else
            fprintf(stderr,"[5955] No CommitEnrollment performed.\\n");
#endif
            result=0;
            break;
        }
    }
#if defined(FT5955_OFFLINE_VERIFY_AFTER_COMMIT)
    if(commit_ok && next_verify<argc){
        fprintf(stderr,"[5955] VERIFY_PROBE held_out=%d; no new scans or saved templates.\n",
                argc-next_verify);
        for(int i=next_verify;i<argc;i++){
            unsigned vw=0,vh=0;
            uint8_t *vpx=read_pgm(argv[i],&vw,&vh);
            if(!vpx){
                ft_engine_probe_wipe_offline();
                return 2;
            }
#if defined(FT5955_OFFLINE_INVERT_INPUT_PIXELS)
            for(size_t j=0;j<(size_t)vw*vh;j++) vpx[j]=(uint8_t)(255u-vpx[j]);
#endif
            uint32_t vhr=ft_engine_accept(vpx,(int)vw,(int)vh,1);
            memset(vpx,0,(size_t)vw*vh);
            free(vpx);
            fprintf(stderr,"[5955] VERIFY_PROBE sample=%d accept_hr=0x%08x\n",
                    i-2,vhr);
            if(vhr==0) ft_engine_probe_verify_current_offline(i-2);
        }
    } else {
        fprintf(stderr,"[5955] VERIFY_PROBE skipped=%s\n",
                commit_ok?"no-held-out-captures":"commit-not-ready");
    }
    ft_engine_probe_wipe_offline();
#endif
    if(result!=0) fprintf(stderr,"[5955] Additional DISTINCT captures required to complete enrolment.\\n");
#if defined(FT5955_OFFLINE_PROBE_COMMIT)
    fprintf(stderr,"[5955] In-memory commit probe finished; no template persisted, printed or saved.\\n");
#else
    fprintf(stderr,"[5955] No biometric template committed, printed, or saved.\\n");
#endif
    return 0; /* successful diagnostic even if enrolment is incomplete */
}
