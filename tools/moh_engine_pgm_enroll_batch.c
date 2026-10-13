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
#if defined(FT5955_OFFLINE_QUERY_EXTENDED_ENROLLMENT_STATUS)
extern void ft_engine_log_extended_enrollment_status(void);
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
    if(argc<5 || argc>23 || strcmp(argv[1],"--pgm-enroll-batch")!=0){
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
    for(int i=3;i<argc;i++){
        unsigned w=0,h=0;
        uint8_t *pixels=read_pgm(argv[i],&w,&h);
        if(!pixels) return 2;
        fprintf(stderr,"[5955] Enrolment sample %d/%d: %ux%u P5 image.\\n",i-2,argc-3,w,h);
        if(w!=64 || h!=80) fprintf(stderr,"[5955] WARNING: image will be cropped/scaled to 64x80.\\n");
        uint32_t hr=ft_engine_accept(pixels,(int)w,(int)h,4);
        memset(pixels,0,(size_t)w*h);
        free(pixels);
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
            fprintf(stderr,"[5955] ENROLLMENT COMPLETE (in memory). No CommitEnrollment performed.\\n");
            result=0;
            break;
        }
    }
    if(result!=0) fprintf(stderr,"[5955] Additional DISTINCT captures required to complete enrolment.\\n");
    fprintf(stderr,"[5955] No biometric template committed, printed, or saved.\\n");
    return 0; /* successful diagnostic even if enrolment is incomplete */
}
