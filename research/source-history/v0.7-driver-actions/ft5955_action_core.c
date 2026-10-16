/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_action_core.h"
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define FT5955_ENROLL_STAGES 12u
#define FT5955_MAX_ENROLL_CAPTURES 96u
#define FT5955_MAX_VERIFY_CAPTURES 16u

void
ft5955_action_begin (Ft5955Action *a, Ft5955ActionKind kind)
{
  if (!a)
    return;
  a->kind = kind;
  a->accepted = 0;
  a->attempts = 0;
  a->completed = 0;
}

Ft5955DriverEvent
ft5955_action_consume (Ft5955Action *a, Ft5955EngineEvent event,
                       unsigned *completed_stages)
{
  unsigned limit;
  if (completed_stages)
    *completed_stages = 0;
  if (!a || a->kind == FT5955_ACTION_IDLE || a->completed)
    return FT5955_DRIVER_INVALID;
  if (event == FT5955_ENGINE_CANCEL)
    {
      a->completed = 1;
      return FT5955_DRIVER_CANCELLED;
    }
  if (event == FT5955_ENGINE_FAULT)
    {
      a->completed = 1;
      return FT5955_DRIVER_FAILED;
    }
  limit = a->kind == FT5955_ACTION_ENROLL ? FT5955_MAX_ENROLL_CAPTURES
                                          : FT5955_MAX_VERIFY_CAPTURES;
  if (++a->attempts > limit)
    {
      a->completed = 1;
      return FT5955_DRIVER_FAILED;
    }
  if (a->kind == FT5955_ACTION_VERIFY)
    {
      if (event == FT5955_ENGINE_RETRY)
        return FT5955_DRIVER_RETRY;
      a->completed = 1;
      if (event == FT5955_ENGINE_MATCH)
        return FT5955_DRIVER_MATCHED;
      if (event == FT5955_ENGINE_NO_MATCH)
        return FT5955_DRIVER_NOT_MATCHED;
      return FT5955_DRIVER_FAILED;
    }
  if (event == FT5955_ENGINE_RETRY)
    {
      if (completed_stages)
        *completed_stages = a->accepted;
      return FT5955_DRIVER_RETRY;
    }
  if (event == FT5955_ENGINE_ADDED && a->accepted < FT5955_ENROLL_STAGES - 1)
    {
      a->accepted++;
      if (completed_stages)
        *completed_stages = a->accepted;
      return FT5955_DRIVER_PROGRESS;
    }
  if (event == FT5955_ENGINE_COMPLETE && a->accepted == FT5955_ENROLL_STAGES - 1)
    {
      a->accepted = FT5955_ENROLL_STAGES;
      if (completed_stages)
        *completed_stages = a->accepted;
      a->completed = 1;
      return FT5955_DRIVER_ENROLLED;
    }
  a->completed = 1;
  return FT5955_DRIVER_FAILED;
}

Ft5955DriverEvent
ft5955_action_consume_reply (Ft5955Action *action, const char *line,
                             unsigned *completed_stages)
{
  unsigned n = 0;
  char extra = 0;
  if (!action || !line || strlen (line) > 63)
    return ft5955_action_consume (action, FT5955_ENGINE_FAULT, completed_stages);
  if (strcmp (line, "RETRY QUALITY") == 0)
    return ft5955_action_consume (action, FT5955_ENGINE_RETRY, completed_stages);
  if (strcmp (line, "COMPLETE") == 0)
    return ft5955_action_consume (action, FT5955_ENGINE_COMPLETE, completed_stages);
  if (strcmp (line, "MATCH") == 0)
    return ft5955_action_consume (action, FT5955_ENGINE_MATCH, completed_stages);
  if (strcmp (line, "NO_MATCH") == 0)
    return ft5955_action_consume (action, FT5955_ENGINE_NO_MATCH, completed_stages);
  if (strcmp (line, "CANCELLED") == 0)
    return ft5955_action_consume (action, FT5955_ENGINE_CANCEL, completed_stages);
  if (action->kind == FT5955_ACTION_ENROLL &&
      sscanf (line, "PROGRESS %u 12%c", &n, &extra) == 1 &&
      n == action->accepted + 1 && n <= 11)
    return ft5955_action_consume (action, FT5955_ENGINE_ADDED, completed_stages);
  /* Unknown replies, malformed, skipped/duplicated stages, engine ERROR. */
  return ft5955_action_consume (action, FT5955_ENGINE_FAULT, completed_stages);
}
