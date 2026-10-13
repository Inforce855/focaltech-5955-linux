/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Experimental no-biometric synthetic image probe. The unverified
 * AcceptSampleData path may crash: run only in isolated bubblewrap test.
 */
#include "ft_engine.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define PROBE_W 64
#define PROBE_H 80
int main(int argc,char **argv)
{
  if(argc!=3 || strcmp(argv[1],"--synthetic-accept")!=0){
    fprintf(stderr,"Usage: %s --synthetic-accept /tmp/engine.dll\n",argv[0]);
    return 2;
  }
  fprintf(stderr,"[5955] SYNTHETIC ACCEPT: generated gradient, NO real fingerprint or USB.\n");
  int attach=ft_engine_open(argv[2]);
  fprintf(stderr,"[5955] Attach wrapper status: %d\n",attach);
  if(attach!=0) return 1;
  uint8_t image[PROBE_W*PROBE_H];
  for(unsigned y=0;y<PROBE_H;y++)
    for(unsigned x=0;x<PROBE_W;x++)
      image[y*PROBE_W+x]=(uint8_t)((x*3u+y*2u)&255u);
  fprintf(stderr,"[5955] Calling AcceptSampleData with synthetic gradient (64x80); purpose=1.\n");
  uint32_t hr=ft_engine_accept(image,PROBE_W,PROBE_H,1);
  fprintf(stderr,"[5955] AcceptSampleData HRESULT: 0x%08x\n",(unsigned)hr);
  fprintf(stderr,"[5955] Diagnostic ONLY: no fingerprint processing or matching demonstrated.\n");
  /* A returned HRESULT, even a failure value, indicates control returned.
   * Do not misrepresent nonzero HRESULT as successful processing. */
  return hr==0 ? 0 : 3;
}
