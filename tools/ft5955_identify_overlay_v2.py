#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""SECOND, isolated FT5955 identify overlay: gallery RETRY and event-only trace.

Apply only AFTER ft5955_identify_overlay.apply_identify_variant() and
apply_timingtrace_variant() in a freshly reconstructed DISPOSABLE libfprint
source tree. The SHA-pinned original identify candidate remains reproducible;
this tool never changes the installed library or saved biometric templates.

The v2 trial does not yet optimise process startup. Its timestamp-only trace
lets us compare USB capture, matcher startup/response and child cleanup
without guessing that the previously fixed one-second relay bug returned.
"""
from __future__ import annotations

from pathlib import Path
from ft5955_identify_overlay import ACTION


def apply_identify_v2_variant(source: Path) -> None:
    target = source / ACTION
    if target.is_symlink() or not target.is_file():
        raise ValueError("Identify v2 requires regular disposable action source")
    original = target.read_text(encoding="utf-8")
    if "FT5955TIMING phase=" not in original:
        raise ValueError("Identify v2 requires the existing timingtrace transform")

    # Every old anchor is required exactly once. No changes on failure.
    replacements = (
        (
            "  borrowed.candidate = *tmpl;\n"
            "  if (!start_gateway (&borrowed, &child, &in, &out, c, err) ||",
            "  borrowed.candidate = *tmpl;\n"
            '  ft5955_trace ("identify_gateway_start");\n'
            "  if (!start_gateway (&borrowed, &child, &in, &out, c, err) ||",
        ),
        (
            '  if (!write_all (out, "FRAME\\n", 6, c, err) ||',
            '  ft5955_trace ("identify_gateway_ready");\n'
            '  if (!write_all (out, "FRAME\\n", 6, c, err) ||',
        ),
        (
            "  if (!reply)\n"
            "    goto cleanup;\n"
            '  if (strcmp (reply, "MATCH") == 0)',
            "  if (!reply)\n"
            "    goto cleanup;\n"
            '  ft5955_trace ("identify_matcher_reply");\n'
            '  if (strcmp (reply, "MATCH") == 0)',
        ),
        (
            "cleanup:\n"
            "  g_free (reply);\n"
            "  if (child)\n",
            "cleanup:\n"
            "  g_free (reply);\n"
            "  if (child)\n",
        ),
        (
            "cleanup:\n"
            "  g_free (reply);\n"
            "  if (child)\n"
            "    {\n",
            "cleanup:\n"
            "  g_free (reply);\n"
            "  if (child)\n"
            "    {\n"
            '      ft5955_trace ("identify_gateway_cleanup_begin");\n',
        ),
        (
            "      g_object_unref (child);\n"
            "    }\n"
            "  if (in)\n",
            "      g_object_unref (child);\n"
            '      ft5955_trace ("identify_gateway_cleanup_done");\n'
            "    }\n"
            "  if (in)\n",
        ),
        (
            "  gboolean decided = FALSE;\n\n"
            "  for (guint attempt = 0;",
            "  gboolean decided = FALSE;\n"
            '  ft5955_trace ("identify_worker_start");\n\n'
            "  for (guint attempt = 0;",
        ),
        (
            "      if (!ft5955_native_scan (job->usb, c, frame, &err))\n"
            "        goto finish;\n\n",
            '      ft5955_trace ("identify_scan_begin");\n'
            "      if (!ft5955_native_scan (job->usb, c, frame, &err))\n"
            "        goto finish;\n"
            '      ft5955_trace ("identify_image_captured");\n\n',
        ),
        (
            "          if (verdict == FT5955_IDENTIFY_RETRY)\n"
            "            {\n"
            "              retry = TRUE;\n"
            "              break;  /* rejected image: require a fresh touch */\n"
            "            }\n",
            "          if (verdict == FT5955_IDENTIFY_RETRY)\n"
            "            {\n"
            '              ft5955_trace ("identify_quality_retry");\n'
            "              retry = TRUE;\n"
            "              /* This candidate cannot decide NO_MATCH. Check\n"
            "               * remaining gallery prints against this SAME frame.\n"
            "               * If none MATCH, require a fresh touch. */\n"
            "              continue;\n"
            "            }\n",
        ),
        (
            "              job->match_index = (gint) i;\n"
            "              decided = TRUE;\n",
            '              ft5955_trace ("identify_match");\n'
            "              job->match_index = (gint) i;\n"
            "              decided = TRUE;\n",
        ),
        (
            "      if (decided || !retry)\n"
            "        {\n"
            "          decided = TRUE; /* includes complete, genuine gallery NO_MATCH */\n"
            "          break;\n"
            "        }\n",
            "      if (decided || !retry)\n"
            "        {\n"
            "          /* A gallery NO_MATCH requires ALL candidates to say\n"
            "           * NO_MATCH. A quality rejection instead needs a new\n"
            "           * physical contact unless another candidate MATCHED. */\n"
            "          if (!decided)\n"
            '            ft5955_trace ("identify_gallery_no_match");\n'
            "          decided = TRUE;\n"
            "          break;\n"
            "        }\n",
        ),
        (
            "finish:\n"
            "  sensitive_clear (frame, sizeof frame);\n",
            "finish:\n"
            '  ft5955_trace ("identify_worker_end");\n'
            "  sensitive_clear (frame, sizeof frame);\n",
        ),
        (
            "  g_autoptr(GError) err = NULL;\n\n"
            "  if (!g_task_propagate_boolean (task, &err))",
            "  g_autoptr(GError) err = NULL;\n"
            '  ft5955_trace ("identify_finish_start");\n\n'
            "  if (!g_task_propagate_boolean (task, &err))",
        ),
        (
            "      fpi_device_identify_complete (dev, g_steal_pointer (&err));\n"
            "      return;\n",
            "      fpi_device_identify_complete (dev, g_steal_pointer (&err));\n"
            '      ft5955_trace ("identify_finish_done");\n'
            "      return;\n",
        ),
        (
            "  fpi_device_identify_complete (dev, NULL);\n"
            "  (void) unused;\n",
            "  fpi_device_identify_complete (dev, NULL);\n"
            '  ft5955_trace ("identify_finish_done");\n'
            "  (void) unused;\n",
        ),
    )
    # One identity "replacement" above is intentionally skipped.
    replacements = tuple((old, new) for old, new in replacements if old != new)

    output = original
    for old, new in replacements:
        if output.count(old) != 1:
            raise ValueError(f"Unexpected identify v2 source anchor: {old[:80]!r}")
        output = output.replace(old, new, 1)

    phases = (
        "identify_gateway_start", "identify_gateway_ready",
        "identify_matcher_reply", "identify_gateway_cleanup_begin",
        "identify_gateway_cleanup_done", "identify_worker_start",
        "identify_scan_begin", "identify_image_captured",
        "identify_quality_retry", "identify_match",
        "identify_gallery_no_match", "identify_worker_end",
        "identify_finish_start", "identify_finish_done",
    )
    if any(output.count(f'"{phase}"') != 1 for phase in phases):
        raise ValueError("Identify v2 timing trace phase count mismatch")

    # No overwrite outside the ephemeral reconstructed source.
    target.write_text(output, encoding="utf-8")
