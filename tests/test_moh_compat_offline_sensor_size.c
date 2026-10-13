/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic only. Never calls vendor DLL.
 */
#include "ft5955_offline_sensor_size.h"
#include <stdio.h>
int main(void){
  unsigned char out[4]={0xaa,0xaa,0xaa,0xaa};
  uint32_t n=123;
  if(ft5955_sim_sensor_ioctl(FT5955_IOCTL_BIOMETRIC_SENSOR_SIZE,out,2,&n)!=1
     || n!=2 || out[0]!=64 || out[1]!=80 || out[2]!=0xaa)
    return 1;
  n=123;
  if(ft5955_sim_sensor_ioctl(FT5955_IOCTL_BIOMETRIC_SENSOR_SIZE,out,1,&n)!=0 || n!=0)
    return 2;
  n=123;
  if(ft5955_sim_sensor_ioctl(0x12345678,out,4,&n)!=0 || n!=0)
    return 3;
  puts("5955 offline-only sensor-size IOCTL: synthetic tests OK");
  return 0;
}
