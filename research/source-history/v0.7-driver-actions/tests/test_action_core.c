/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ft5955_action_core.h"
#include <assert.h>
#include <stdio.h>

static void test_enroll (void)
{
  Ft5955Action a;
  unsigned n;
  ft5955_action_begin (&a, FT5955_ACTION_ENROLL);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_RETRY, &n) == FT5955_DRIVER_RETRY);
  assert (n == 0 && a.accepted == 0);
  for (unsigned i = 1; i < 12; i++)
    {
      assert (ft5955_action_consume (&a, FT5955_ENGINE_ADDED, &n) == FT5955_DRIVER_PROGRESS);
      assert (n == i && a.accepted == i);
      assert (ft5955_action_consume (&a, FT5955_ENGINE_RETRY, &n) == FT5955_DRIVER_RETRY);
      assert (n == i && a.accepted == i);
    }
  assert (ft5955_action_consume (&a, FT5955_ENGINE_COMPLETE, &n) == FT5955_DRIVER_ENROLLED);
  assert (n == 12 && a.completed == 1);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_COMPLETE, &n) == FT5955_DRIVER_INVALID);
}
static void test_fail_closed (void)
{
  Ft5955Action a;
  unsigned n;
  ft5955_action_begin (&a, FT5955_ACTION_ENROLL);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_COMPLETE, &n) == FT5955_DRIVER_FAILED);
  ft5955_action_begin (&a, FT5955_ACTION_ENROLL);
  for (unsigned i = 0; i < 96; i++)
    assert (ft5955_action_consume (&a, FT5955_ENGINE_RETRY, &n) == FT5955_DRIVER_RETRY);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_RETRY, &n) == FT5955_DRIVER_FAILED);
  ft5955_action_begin (&a, FT5955_ACTION_ENROLL);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_CANCEL, &n) == FT5955_DRIVER_CANCELLED);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_ADDED, &n) == FT5955_DRIVER_INVALID);
}
static void test_protocol (void)
{
  Ft5955Action a;
  unsigned n;
  ft5955_action_begin (&a, FT5955_ACTION_ENROLL);
  assert (ft5955_action_consume_reply (&a, "PROGRESS 1 12", &n) == FT5955_DRIVER_PROGRESS);
  assert (n == 1);
  assert (ft5955_action_consume_reply (&a, "PROGRESS 3 12", &n) == FT5955_DRIVER_FAILED);
  ft5955_action_begin (&a, FT5955_ACTION_ENROLL);
  assert (ft5955_action_consume_reply (&a, "PROGRESS 1 12XYZ", &n) == FT5955_DRIVER_FAILED);
  ft5955_action_begin (&a, FT5955_ACTION_ENROLL);
  assert (ft5955_action_consume_reply (&a, "MATCH", &n) == FT5955_DRIVER_FAILED);
  ft5955_action_begin (&a, FT5955_ACTION_VERIFY);
  assert (ft5955_action_consume_reply (&a, "NO_MATCH", &n) == FT5955_DRIVER_NOT_MATCHED);
}
static void test_verify (void)
{
  Ft5955Action a;
  unsigned n;
  ft5955_action_begin (&a, FT5955_ACTION_VERIFY);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_RETRY, &n) == FT5955_DRIVER_RETRY);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_MATCH, &n) == FT5955_DRIVER_MATCHED);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_NO_MATCH, &n) == FT5955_DRIVER_INVALID);
  ft5955_action_begin (&a, FT5955_ACTION_VERIFY);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_NO_MATCH, &n) == FT5955_DRIVER_NOT_MATCHED);
  ft5955_action_begin (&a, FT5955_ACTION_VERIFY);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_COMPLETE, &n) == FT5955_DRIVER_FAILED);
  ft5955_action_begin (&a, FT5955_ACTION_VERIFY);
  assert (ft5955_action_consume (&a, FT5955_ENGINE_FAULT, &n) == FT5955_DRIVER_FAILED);
}
int main (void)
{
  test_enroll ();
  test_fail_closed ();
  test_verify ();
  test_protocol ();
  puts ("PASS: FT5955 12 accepted stages, quality retries, bounded attempts, verify, cancellation and protocol failures");
  return 0;
}
