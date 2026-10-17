/* Synthetic-only engine for testing template IPC and sandbox restarts. */
#include "ft_engine.h"
#include <stdlib.h>
#include <string.h>
static uint8_t last;
static int scans, begun;
int ft_engine_open(const char *path){return path?0:-1;}
int ft_engine_enroll_begin(void){scans=0;begun=1;return 0;}
uint32_t ft_engine_accept(const uint8_t *img,int w,int h,uint8_t purpose){
    if(!img || w!=64 || h!=80 || (purpose!=1&&purpose!=4))return 1;
    last=img[0];
    return last==0?UINT32_C(0x80098008):0;
}
int ft_engine_enroll_update(void){if(!begun)return -1;return ++scans==12?0:1;}
int ft_engine_enroll_commit(uint8_t **out,size_t *len){
    *out=malloc(16);
    if(!*out)return -1;
    memset(*out,last,16);*len=16;return 0;
}
int ft_engine_verify(const uint8_t *buf,size_t n){return n==16 && buf[0]==last;}
int ft_engine_probe_duplicate_offline(void){return 0;}
void ft_engine_probe_wipe_offline(void){}
uint8_t ft_engine_probe_record_subfactor_offline(void){return 7;}
void ft_engine_probe_select_subfactor_offline(uint8_t subtype){(void)subtype;}
