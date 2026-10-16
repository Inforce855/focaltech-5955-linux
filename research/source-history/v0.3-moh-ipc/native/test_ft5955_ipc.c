/* Synthetic-only C client integration regression test. No USB or vendor DLL. */
#include "ft5955_ipc.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void expected(const char *actual,const char *want) {
    if(strcmp(actual,want)){fprintf(stderr,"Expected '%s', got '%s'\n",want,actual);exit(1);}
}
int main(int argc,char **argv) {
    if(argc!=4){fprintf(stderr,"usage: test_ft5955_ipc python adapter fake-runner\n");return 2;}
    Ft5955Ipc ipc=FT5955_IPC_INIT;
    char reply[FT5955_REPLY_BYTES];
    uint8_t frame[FT5955_FRAME_BYTES];
    if(ft5955_ipc_start(&ipc,argv[1],argv[2],argv[3],5000))return 3;
    expected((ft5955_ipc_begin(&ipc,1,reply)==0)?reply:"IPC_FAIL","BEGIN OK");
    memset(frame,0,sizeof frame);
    expected((ft5955_ipc_sample(&ipc,frame,reply)==0)?reply:"IPC_FAIL","RETRY QUALITY");
    for(int slot=1;slot<=2;slot++) {
        if(slot==2) expected((ft5955_ipc_begin(&ipc,slot,reply)==0)?reply:"IPC_FAIL","BEGIN OK");
        memset(frame,7,sizeof frame);
        for(int n=1;n<=12;n++) {
            if(ft5955_ipc_sample(&ipc,frame,reply)) return 4;
            if(n==12) expected(reply,"COMPLETE");
            else {char want[64];snprintf(want,sizeof want,"PROGRESS %d 12",n);expected(reply,want);}
        }
    }
    const char *results[]={"RETRY QUALITY","MATCH 1","MATCH 2","NO_MATCH","AMBIGUOUS"};
    for(int i=0;i<5;i++) {
        memset(frame,i,sizeof frame);
        expected((ft5955_ipc_verify(&ipc,frame,reply)==0)?reply:"IPC_FAIL",results[i]);
    }
    expected((ft5955_ipc_cancel(&ipc,reply)==0)?reply:"IPC_FAIL","CANCELLED");
    expected((ft5955_ipc_verify(&ipc,frame,reply)==0)?reply:"IPC_FAIL","ERROR BAD_STATE");
    int stage=0;
    assert(ft5955_ipc_decode("PROGRESS 11 12",&stage)==FT5955_R_PROGRESS && stage==11);
    assert(ft5955_ipc_decode("PROGRESS 12 12",&stage)==FT5955_R_INVALID);
    assert(ft5955_ipc_decode("PROGRESS -1 12",&stage)==FT5955_R_INVALID);
    assert(ft5955_ipc_decode("MATCH 1",&stage)==FT5955_R_MATCH_1);
    assert(ft5955_ipc_decode("MATCH 2",&stage)==FT5955_R_MATCH_2);
    assert(ft5955_ipc_decode("COMPLETE",&stage)==FT5955_R_COMPLETE);
    assert(ft5955_ipc_decode("ERROR BAD_STATE",&stage)==FT5955_R_ERROR);
    assert(ft5955_ipc_decode("NO_MATCH",&stage)==FT5955_R_NO_MATCH);
    ft5955_ipc_close(&ipc);
    puts("PASS: native C IPC client, 24 accepted stages, quality retry, identification and cancel");
    return 0;
}
