/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Offline ABI test. No vendor DLL or biometric data.
 */
#include "ft5955_winbio_interface_probe.h"
#include <stdio.h>
int main(void) {
  ft5955_winbio_interface_probe sensor, storage;
  ft5955_winbio_interface_probe_init(&sensor,FT5955_WINBIO_SENSOR_TYPE);
  ft5955_winbio_interface_probe_init(&storage,FT5955_WINBIO_STORAGE_TYPE);
  if(sensor.version_major!=3 || sensor.version_minor!=0 ||
     sensor.type!=1 || storage.type!=3 ||
     sensor.size!=0x100 || storage.size!=0x100 ||
     FT5955_WINBIO_PROBE_SLOTS!=28 ||
     sensor.slots[0]!=0 || storage.slots[27]!=0) {
      fputs("WinBio table header probe failed\n",stderr); return 1;
  }
  puts("5955 sensor/storage synthetic interface header ABI: tests OK");
  return 0;
}
