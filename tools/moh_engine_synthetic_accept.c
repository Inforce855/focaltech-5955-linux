/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic, offline only. Generates simple wave-like stripes, not a print.
 * Runs only under the isolated bwrap test harness, without USB or biometrics.
 */
#include "ft_engine.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define PROBE_W 64
#define PROBE_H 80
#define WINBIO_E_BAD_CAPTURE 0x80098008u
int main(int argc,char **argv)
{
  if(argc<3 || argc>4 || strcmp(argv[1],"--synthetic-accept")!=0 ||
     (argc==4 && strcmp(argv[3],"gradient")!=0 && strcmp(argv[3],"waves")!=0)){
    fprintf(stderr,"Usage: %s --synthetic-accept /tmp/engine.dll [gradient|waves]\n",argv[0]);
    return 2;
  }
  const int waves=argc==4 && strcmp(argv[3],"waves")==0;
  fprintf(stderr,"[5955] SYNTHETIC ACCEPT: pattern=%s; NO fingerprint or USB.\n",
          waves?"waves":"gradient");
  int attach=ft_engine_open(argv[2]);
  fprintf(stderr,"[5955] Attach wrapper status: %d\n",attach);
  if(attach!=0) return 1;
  uint8_t image[PROBE_W*PROBE_H];
  for(unsigned y=0;y<PROBE_H;y++)
    for(unsigned x=0;x<PROBE_W;x++){
      if(!waves) image[y*PROBE_W+x]=(uint8_t)((x*3u+y*2u)&255u);
      else {
        /* Analytic alternating lines with a slight curvature. No print
         * image, template, minutiae, or capture data are involved. */
        double phase=(double)x*0.78+2.1*sin((double)y*0.055);
        image[y*PROBE_W+x]=(sin(phase)>0.0)?200u:42u;
      }
    }
  fprintf(stderr,"[5955] Calling AcceptSampleData with %s (64x80), purpose=1.\n",
          waves?"synthetic waves":"synthetic gradient");
  uint32_t hr=ft_engine_accept(image,PROBE_W,PROBE_H,1);
  fprintf(stderr,"[5955] AcceptSampleData HRESULT: 0x%08x\n",(unsigned)hr);
  if(hr==0)
    fprintf(stderr,"[5955] RESULT: synthetic sample accepted (not a fingerprint match).\n");
  else if(hr==WINBIO_E_BAD_CAPTURE)
    fprintf(stderr,"[5955] RESULT: engine rejected synthetic sample as a bad capture; call returned normally.\n");
  else
    fprintf(stderr,"[5955] RESULT: unexpected HRESULT from image processing.\n");
  return (hr==0 || hr==WINBIO_E_BAD_CAPTURE)?0:3;
}
