/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Isolated offline engine-interface smoke-test. NO Attach/USB/enrolment.
 * Only execute in a trusted, isolated environment after import/ABI review.
 */
#include <stdio.h>
#include <string.h>
#include "ft_engine.h"

int main(int argc, char **argv)
{
  if (argc != 3 || strcmp(argv[1], "--query-interface") != 0)
    {
      fprintf(stderr, "Usage: %s --query-interface /private/path/ftWbioEngineAdapter.dll\n", argv[0]);
      return 2;
    }
  fprintf(stderr, "[5955] Query only: no USB, enrolment or fingerprint files.\n");
  int status = ft_engine_smoke_interface(argv[2]);
  fprintf(stderr, "[5955] Query interface status: %d\n", status);
  return status == 0 ? 0 : 1;
}
