/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Interactive, session-persistent isolated MOH enrolment.
 * Binary stdin: 5120 bytes per 64x80 P5-derived grayscale frame.
 * Machine-readable stdout: READY, TOUCH <n> <state>, DONE.
 * No template commit, storage, USB, image printing or network.
 */
#include "ft_engine.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define W 64
#define H 80
#define BAD_CAPTURE UINT32_C(0x80098008)
static int get_frame(uint8_t *data) {
  size_t filled=0;
  while (filled<W*H) {
    size_t n=fread(data+filled,1,W*H-filled,stdin);
    if(!n) return filled==0 && feof(stdin)?0:-1;
    filled+=n;
  }
  return 1;
}
int main(int argc,char **argv) {
  if(argc!=3 || strcmp(argv[1],"--interactive-enroll")) return 2;
  setvbuf(stdout,NULL,_IOLBF,0);
  if(ft_engine_open(argv[2])!=0) { puts("ERROR attach"); return 1; }
  if(ft_engine_enroll_begin()!=0) { puts("ERROR create-enrollment"); return 3; }
  puts("READY");
  uint8_t image[W*H];
  for(int i=1;i<=96;i++) {
    int n=get_frame(image);
    if(n==0) { puts("DONE stopped"); return 0; }
    if(n<0) { puts("ERROR incomplete-frame"); return 3; }
    uint32_t hr=ft_engine_accept(image,W,H,4);
    memset(image,0,sizeof image);
    if(hr==BAD_CAPTURE) { printf("TOUCH %d bad-capture\n",i); continue; }
    if(hr) { printf("ERROR accept-%08x\n",(unsigned)hr); return 3; }
    int status=ft_engine_enroll_update();
    if(status==0) { printf("TOUCH %d complete\n",i); puts("DONE complete"); return 0; }
    if(status==1) { printf("TOUCH %d added\n",i); continue; }
    if(status==2) { printf("TOUCH %d rejected\n",i); continue; }
    printf("ERROR enrollment-%d\n",status);
    return 3;
  }
  puts("DONE limit");
  return 0;
}
