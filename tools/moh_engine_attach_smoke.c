/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Experimental offline MOH Attach reconnaissance. Never captures a print.
 * Compile ONLY with the two opt-in defines and execute under bubblewrap.
 */
#include "ft_engine.h"
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv)
{
  if(argc!=3 || strcmp(argv[1],"--attach-offline")!=0){
    fprintf(stderr,"Usage: %s --attach-offline /tmp/engine.dll\n",argv[0]);
    return 2;
  }
  fprintf(stderr,"[5955] ISOLATED ATTACH: no USB, files or biometric inputs.\n");
  int result=ft_engine_open(argv[2]);
  fprintf(stderr,"[5955] Attach wrapper status: %d\n",result);
  if(result!=0)
    fprintf(stderr,"[5955] Attach did not complete. Treat failure as diagnostic only.\n");
  else
    fprintf(stderr,"[5955] Attach returned success; matching remains unverified.\n");
  return result==0 ? 0 : 1;
}
