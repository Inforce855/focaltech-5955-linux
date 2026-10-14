/* SPDX-License-Identifier: LGPL-2.1-or-later
 * EXPERIMENTAL two-finger, memory-only live identification probe.
 * Run solely behind test_moh_isolated_live_identify.sh (bubblewrap, NO USB).
 *
 * stdin framing: exactly one command byte followed by 5120 grayscale bytes:
 *   '1' = capture for Finger 1 enrolment
 *   '2' = capture for Finger 2 enrolment
 *   'V' = fresh captured image to verify against both stored templates
 *   'Q' = end session immediately; no following image
 * stdout: READY; ENROL <1|2> <ADDED|REJECTED|COMPLETE>; IDENTIFY <1|2|NONE|AMBIGUOUS>;
 *         ERROR <reason>; DONE
 *
 * The vendor templates exist only inside this sandbox's memory. Nothing is
 * written to a file, printed, sent over a network or installed for Linux login.
 * This is a functional experiment, NOT an authentication policy.
 */
#include "ft_engine.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define W 64
#define H 80
#define SIZE (W*H)
#define BAD_CAPTURE UINT32_C(0x80098008)
#define MAX_TEMPLATE (1u<<20)
#define LIMIT 96

#if !defined(FT5955_OFFLINE_VERIFY_AFTER_COMMIT) || \
    !defined(FT5955_OFFLINE_MOCK_EMPTY_QUERY_BY_CONTENT) || \
    !defined(FT5955_OFFLINE_PROBE_DUPLICATE) || \
    !defined(FT5955_OFFLINE_SKIP_ENROLLMENT_STATUS)
#error "Live identification requires the audited offline mock-storage workflow"
#endif

extern int ft_engine_probe_duplicate_offline(void);
extern void ft_engine_probe_wipe_offline(void);
extern uint8_t ft_engine_probe_record_subfactor_offline(void);
extern void ft_engine_probe_select_subfactor_offline(uint8_t subtype);

struct finger {
    uint8_t *template_bytes;
    size_t template_len;
    uint8_t subfactor;
    int ready;
    unsigned attempts;
};
static struct finger fingers[2];

static void wipe(void *ptr,size_t size){
    volatile uint8_t *p=(volatile uint8_t *)ptr;
    while(size--) *p++=0;
}
static void finish(void){
    ft_engine_probe_wipe_offline();
    for(unsigned i=0;i<2;i++){
        if(fingers[i].template_bytes){
            wipe(fingers[i].template_bytes,fingers[i].template_len);
            free(fingers[i].template_bytes);
            fingers[i].template_bytes=NULL;
            fingers[i].template_len=0;
            fingers[i].subfactor=0;
            fingers[i].ready=0;
        }
    }
}
static int read_frame(uint8_t *frame){
    size_t n=0;
    while(n<SIZE){
        size_t k=fread(frame+n,1,SIZE-n,stdin);
        if(k==0) return -1;
        n+=k;
    }
    return 0;
}
static int enroll(int slot,const uint8_t *image){
    struct finger *f=&fingers[slot];
    if(f->ready || (slot==1 && !fingers[0].ready) ||
       ++f->attempts>LIMIT){
        puts("ERROR invalid-enrolment-state");
        return -1;
    }
    if(f->attempts==1 && ft_engine_enroll_begin()!=0){
        puts("ERROR create-enrollment");
        return -1;
    }
    uint32_t hr=ft_engine_accept(image,W,H,4);
    if(hr==BAD_CAPTURE){
        printf("ENROL %d REJECTED\n",slot+1);
        return 0;
    }
    if(hr!=0){
        puts("ERROR enrollment-accept");
        return -1;
    }
    int update=ft_engine_enroll_update();
    if(update==1){
        printf("ENROL %d ADDED\n",slot+1);
        return 0;
    }
    if(update==2){
        printf("ENROL %d REJECTED\n",slot+1);
        return 0;
    }
    if(update!=0){
        puts("ERROR enrollment-update");
        return -1;
    }
    /* Duplicate check works only with an initially empty mock storage
     * adapter; previous finger is held separately in process-private RAM.
     * BeginEnrollment resets the mock record before every new finger. */
    if(ft_engine_probe_duplicate_offline()!=0){
        puts("ERROR duplicate-precheck");
        return -1;
    }
    uint8_t *temp=NULL;
    size_t size=0;
    if(ft_engine_enroll_commit(&temp,&size)!=0 ||
       !temp || !size || size>MAX_TEMPLATE){
        if(temp){wipe(temp,size<=MAX_TEMPLATE?size:0);free(temp);}
        puts("ERROR enrollment-commit");
        return -1;
    }
    f->template_bytes=temp;
    f->template_len=size;
    f->subfactor=ft_engine_probe_record_subfactor_offline();
    f->ready=1;
    ft_engine_probe_wipe_offline();
    printf("ENROL %d COMPLETE\n",slot+1);
    return 0;
}
static int identify(const uint8_t *image){
    if(!fingers[0].ready || !fingers[1].ready){
        puts("ERROR enroll-both-first");
        return -1;
    }
    unsigned matches=0;
    for(int i=0;i<2;i++){
        /* Some vendor matchers consume their current feature set. Re-accept
         * the same held-out frame for EACH candidate, with no new USB read. */
        uint32_t a=ft_engine_accept(image,W,H,1);
        if(a==BAD_CAPTURE){
            puts("IDENTIFY REJECTED");
            return 0;
        }
        if(a!=0){
            puts("ERROR verification-accept");
            return -1;
        }
        ft_engine_probe_select_subfactor_offline(fingers[i].subfactor);
        int m=ft_engine_verify(fingers[i].template_bytes,fingers[i].template_len);
        if(m<0){
            puts("ERROR verification-engine");
            return -1;
        }
        if(m==1) matches|=(unsigned)(1u<<i);
    }
    switch(matches){
    case 0: puts("IDENTIFY NONE");break;
    case 1: puts("IDENTIFY 1");break;
    case 2: puts("IDENTIFY 2");break;
    default: puts("IDENTIFY AMBIGUOUS");break;
    }
    return 0;
}
int main(int argc,char **argv){
    if(argc!=3 || strcmp(argv[1],"--live-identify")!=0) return 2;
    setvbuf(stdout,NULL,_IOLBF,0);
    if(ft_engine_open(argv[2])!=0){puts("ERROR attach");return 3;}
    puts("READY");
    uint8_t frame[SIZE]={0};
    int result=0;
    for(int n=0;n<256;n++){
        int command=fgetc(stdin);
        if(command==EOF || command=='Q') break;
        if(command!='1' && command!='2' && command!='V'){
            puts("ERROR invalid-command");result=3;break;
        }
        if(read_frame(frame)!=0){
            puts("ERROR truncated-frame");result=3;break;
        }
        int status;
        if(command=='V') status=identify(frame);
        else status=enroll(command-'1',frame);
        wipe(frame,sizeof frame);
        if(status!=0){result=3;break;}
    }
    wipe(frame,sizeof frame);
    finish();
    puts("DONE");
    return result;
}
