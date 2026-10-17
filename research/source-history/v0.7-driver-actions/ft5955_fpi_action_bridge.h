/* SPDX-License-Identifier: LGPL-2.1-or-later
 * This mapping MUST run on libfprint's main context, not a USB / IPC worker.
 * Not an installed driver. Called when a validated engine reply arrives.
 */
#ifndef FT5955_FPI_ACTION_BRIDGE_H
#define FT5955_FPI_ACTION_BRIDGE_H
#include "fprint.h"
#include "ft5955_action_core.h"
#include <stdint.h>
#include <stddef.h>

/* Returns TRUE for nonterminal events; FALSE after terminal completion.
 * Calls exactly ONE validated state transition per actual MOH response.
 * For a successful ENROLL COMPLETE: supply the vendor template and recorded
 * subfactor, all from the isolated MOH engine. Other events ignore them.
 * Never save image/template data in this helper.
 */
gboolean ft5955_fpi_apply_reply (FpDevice *device, Ft5955Action *action,
                                const char *moh_reply,
                                const uint8_t *vendor_template,
                                size_t vendor_template_len,
                                uint8_t subfactor);
#endif
