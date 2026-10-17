/* SPDX-License-Identifier: LGPL-2.1-or-later
 * EXPERIMENTAL, private, memory-only FocalTech MOH template restart test.
 * Must run under existing audited test_moh_isolated_live_identify.sh sandbox.
 * Protocol on anonymous stdin/stdout pipes; NEVER attach a terminal to stdout.
 * No filesystem access, persistent database, or authentication decisions.
 */
#include "ft_engine.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define W 64
#define H 80
#define FRAME (W*H)
#define MAX_TEMPLATE (1u<<20)
#define MAX_ATTEMPTS 96
#define BAD_CAPTURE UINT32_C(0x80098008)

extern int ft_engine_probe_duplicate_offline(void);
extern void ft_engine_probe_wipe_offline(void);
extern uint8_t ft_engine_probe_record_subfactor_offline(void);
extern void ft_engine_probe_select_subfactor_offline(uint8_t subtype);

static uint8_t *tmpl;
static size_t tmpl_len;
static uint8_t subfactor;
static unsigned attempts, accepted;
static int completed;

static void secure_zero(void *p, size_t n) {
    volatile unsigned char *b = (volatile unsigned char *)p;
    while (n--) *b++ = 0;
}
static void discard(void) {
    if (tmpl) { secure_zero(tmpl,tmpl_len);free(tmpl);tmpl=NULL; }
    tmpl_len=0;subfactor=0;
    ft_engine_probe_wipe_offline();
}
static int read_all(void *dst,size_t count){
    unsigned char *p=dst;
    while (count) {
        size_t n=fread(p,1,count,stdin);
        if (!n) return -1;
        p+=n;count-=n;
    }
    return 0;
}
static int write_all(const void *data,size_t count){
    if (fwrite(data,1,count,stdout)!=count || fflush(stdout)) return -1;
    return 0;
}
static int enroll_one(const uint8_t *image){
    if (completed || ++attempts>MAX_ATTEMPTS) {puts("ERROR ENROLL_STATE");return -1;}
    if (attempts==1 && ft_engine_enroll_begin()!=0) {puts("ERROR ENROLL_BEGIN");return -1;}
    uint32_t hr=ft_engine_accept(image,W,H,4);
    if (hr==BAD_CAPTURE) {puts("RETRY QUALITY");return 0;}
    if (hr!=0) {puts("ERROR ACCEPT");return -1;}
    int st=ft_engine_enroll_update();
    if (st==1) {
        if (++accepted>=12) {puts("ERROR PROGRESS");return -1;}
        printf("PROGRESS %u 12\n",accepted);
        return 0;
    }
    if (st==2) {puts("RETRY QUALITY");return 0;}
    if (st!=0 || accepted!=11) {puts("ERROR ENROLL_UPDATE");return -1;}
    if (ft_engine_probe_duplicate_offline()!=0) {puts("ERROR DUPLICATE");return -1;}
    if (ft_engine_enroll_commit(&tmpl,&tmpl_len)!=0 || !tmpl || !tmpl_len || tmpl_len>MAX_TEMPLATE) {
        puts("ERROR COMMIT");return -1;
    }
    subfactor=ft_engine_probe_record_subfactor_offline();
    completed=1;accepted=12;
    ft_engine_probe_wipe_offline();
    puts("COMPLETE");
    return 0;
}
static int export_template(void){
    if (!completed || !tmpl || !tmpl_len) {puts("ERROR NO_TEMPLATE");return -1;}
    printf("TEMPLATE %zu %u\n",tmpl_len,(unsigned)subfactor);
    if (fflush(stdout) || write_all(tmpl,tmpl_len)) return -1;
    return 0;
}
static int import_template(void){
    /* Fixed 5-byte header: 32-bit little-endian payload size, 8-bit subfactor. */
    uint8_t header[5];
    if (completed || tmpl || read_all(header,sizeof header)) {puts("ERROR IMPORT_STATE");return -1;}
    uint32_t n=(uint32_t)header[0] | ((uint32_t)header[1]<<8) |
               ((uint32_t)header[2]<<16) | ((uint32_t)header[3]<<24);
    if (!n || n>MAX_TEMPLATE) {puts("ERROR TEMPLATE_SIZE");return -1;}
    uint8_t *copy=malloc(n);
    if (!copy) {puts("ERROR NO_MEMORY");return -1;}
    if (read_all(copy,n)) {secure_zero(copy,n);free(copy);puts("ERROR IMPORT_TRUNCATED");return -1;}
    tmpl=copy;tmpl_len=n;subfactor=header[4];completed=1;
    puts("IMPORTED");
    return 0;
}
static int verify_one(const uint8_t *image){
    if (!completed || !tmpl) {puts("ERROR NO_TEMPLATE");return -1;}
    uint32_t hr=ft_engine_accept(image,W,H,1);
    if (hr==BAD_CAPTURE) {puts("RETRY QUALITY");return 0;}
    if (hr!=0) {puts("ERROR VERIFY_ACCEPT");return -1;}
    ft_engine_probe_select_subfactor_offline(subfactor);
    int result=ft_engine_verify(tmpl,tmpl_len);
    if (result<0) {puts("ERROR VERIFY_ENGINE");return -1;}
    puts(result==1?"MATCH":"NO_MATCH");
    return 0;
}
int main(int argc,char **argv){
    if(argc!=3 || strcmp(argv[1],"--live-identify"))return 2;
    setvbuf(stdout,NULL,_IONBF,0);
    if(ft_engine_open(argv[2])!=0){puts("ERROR OPEN");return 3;}
    puts("READY");
    int result=0;
    uint8_t frame[FRAME]={0};
    for (unsigned command_count=0;command_count<256;command_count++) {
        int cmd=fgetc(stdin);
        if (cmd==EOF || cmd=='Q') break;
        int st=0;
        switch(cmd){
        case 'E':
            if(read_all(frame,sizeof frame)){puts("ERROR TRUNCATED_FRAME");st=-1;break;}
            st=enroll_one(frame);break;
        case 'V':
            if(read_all(frame,sizeof frame)){puts("ERROR TRUNCATED_FRAME");st=-1;break;}
            st=verify_one(frame);break;
        case 'X': st=export_template();break;
        case 'I': st=import_template();break;
        default: puts("ERROR COMMAND");st=-1;break;
        }
        secure_zero(frame,sizeof frame);
        if(st){result=3;break;}
    }
    secure_zero(frame,sizeof frame);
    discard();
    puts("DONE");
    return result;
}
