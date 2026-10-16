/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Experimental synchronous process boundary for the isolated MOH research
 * engine. Call from a worker thread, never a GLib/libfprint main callback.
 * No frame/template is ever written to a file by this interface.
 */
#ifndef FT5955_IPC_H
#define FT5955_IPC_H
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
#define FT5955_FRAME_BYTES 5120u
#define FT5955_REPLY_BYTES 128u

typedef struct {
    pid_t pid;
    int to_child;
    int from_child;
    int timeout_ms;
    int running;
} Ft5955Ipc;
#define FT5955_IPC_INIT { .pid=-1, .to_child=-1, .from_child=-1, .timeout_ms=0, .running=0 }

/* python, adapter.py and runner.sh must name trusted local executables.
 * This starts the Python protocol adapter, not the DLL: the runner performs
 * existing SHA256 checks and bubblewrap isolation. */
int ft5955_ipc_start(Ft5955Ipc *ipc, const char *python,
                     const char *adapter, const char *runner,
                     int timeout_ms);
/* Returns 0 on IPC success, -1 on failure. Replies are bounded ASCII lines
 * including: BEGIN OK, PROGRESS n 12, RETRY QUALITY, COMPLETE, MATCH 1,
 * MATCH 2, NO_MATCH, AMBIGUOUS, CANCELLED and ERROR ... . No auth policy.
 */
int ft5955_ipc_begin(Ft5955Ipc *ipc, int slot, char reply[FT5955_REPLY_BYTES]);
int ft5955_ipc_sample(Ft5955Ipc *ipc, const uint8_t frame[FT5955_FRAME_BYTES],
                      char reply[FT5955_REPLY_BYTES]);
int ft5955_ipc_verify(Ft5955Ipc *ipc, const uint8_t frame[FT5955_FRAME_BYTES],
                      char reply[FT5955_REPLY_BYTES]);
int ft5955_ipc_cancel(Ft5955Ipc *ipc, char reply[FT5955_REPLY_BYTES]);
/* Fail-closed decoding of the adapter's bounded text results, ready for
 * mapping into libfprint's progress/retry/match notifications. No decision
 * from this test protocol is suitable for user authentication yet. */
typedef enum {
    FT5955_R_INVALID=0, FT5955_R_BEGIN, FT5955_R_PROGRESS,
    FT5955_R_RETRY, FT5955_R_COMPLETE,
    FT5955_R_MATCH_1, FT5955_R_MATCH_2, FT5955_R_NO_MATCH,
    FT5955_R_AMBIGUOUS, FT5955_R_CANCELLED, FT5955_R_ERROR
} Ft5955Result;
Ft5955Result ft5955_ipc_decode(const char *reply, int *stage);

/* Close pipes, terminate/reap child. Safe after partial start. */
void ft5955_ipc_close(Ft5955Ipc *ipc);
#endif
