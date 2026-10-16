/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Pure state machine for a host-matched FT5955 FpDevice driver.
 * No USB, no biometric pixels, no vendor DLL, no GLib in this layer.
 */
#ifndef FT5955_ACTION_CORE_H
#define FT5955_ACTION_CORE_H

typedef enum {
  FT5955_ACTION_IDLE=0,
  FT5955_ACTION_ENROLL,
  FT5955_ACTION_VERIFY
} Ft5955ActionKind;

typedef enum {
  FT5955_ENGINE_ADDED=1,      /* MOH needs another accepted stage */
  FT5955_ENGINE_COMPLETE,     /* MOH has committed 12 accepted stages */
  FT5955_ENGINE_RETRY,        /* bad quality: do not advance */
  FT5955_ENGINE_MATCH,
  FT5955_ENGINE_NO_MATCH,
  FT5955_ENGINE_FAULT,
  FT5955_ENGINE_CANCEL
} Ft5955EngineEvent;

typedef enum {
  FT5955_DRIVER_INVALID=0,
  FT5955_DRIVER_PROGRESS,
  FT5955_DRIVER_RETRY,
  FT5955_DRIVER_ENROLLED,
  FT5955_DRIVER_MATCHED,
  FT5955_DRIVER_NOT_MATCHED,
  FT5955_DRIVER_FAILED,
  FT5955_DRIVER_CANCELLED
} Ft5955DriverEvent;

typedef struct {
  Ft5955ActionKind kind;
  unsigned accepted;
  unsigned attempts;
  unsigned completed;
} Ft5955Action;

/* The engine owns sample quality and enrolment progress. This state machine
 * enforces monotonic, exactly-12 accepted stages and bounded rejected tries.
 * A 'complete' before eleven ADDED replies is a fatal engine protocol error.
 */
void ft5955_action_begin (Ft5955Action *action, Ft5955ActionKind kind);
/* Parse the v0.4 MOH engine textual result and reject skipped/repeated stage
 * numbers. Match/No-match are for VERIFY only. No biometric bytes accepted. */
Ft5955DriverEvent ft5955_action_consume_reply (Ft5955Action *action,
                                               const char *ascii_reply,
                                               unsigned *completed_stages);
Ft5955DriverEvent ft5955_action_consume (Ft5955Action *action,
                                         Ft5955EngineEvent event,
                                         unsigned *completed_stages);
#endif
