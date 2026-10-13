/* SPDX-License-Identifier: LGPL-2.1-or-later
 * WINBIO_PIPELINE x64 field layout, per Microsoft winbio_adapter.h.
 * This is an inert layout definition, NOT an Attach-ready pipeline.
 * No sensor/storage callback signatures are asserted here.
 */
#ifndef FT5955_WINBIO_PIPELINE_H
#define FT5955_WINBIO_PIPELINE_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    void *sensor_handle;        /* +0x00 */
    void *engine_handle;        /* +0x08 */
    void *storage_handle;       /* +0x10 */
    void *sensor_interface;     /* +0x18 */
    void *engine_interface;     /* +0x20 */
    void *storage_interface;    /* +0x28 */
    void *sensor_context;       /* +0x30 */
    void *engine_context;       /* +0x38 */
    void *storage_context;      /* +0x40 */
    void *framework_interface;  /* +0x48 */
} ft5955_winbio_pipeline;

_Static_assert(sizeof(void*)==8, "Windows x64 pointers required");
_Static_assert(sizeof(ft5955_winbio_pipeline)==0x50, "WINBIO_PIPELINE x64 size");
_Static_assert(offsetof(ft5955_winbio_pipeline,engine_handle)==0x08,"EngineHandle");
_Static_assert(offsetof(ft5955_winbio_pipeline,sensor_interface)==0x18,"SensorInterface");
_Static_assert(offsetof(ft5955_winbio_pipeline,engine_interface)==0x20,"EngineInterface");
_Static_assert(offsetof(ft5955_winbio_pipeline,storage_interface)==0x28,"StorageInterface");
_Static_assert(offsetof(ft5955_winbio_pipeline,engine_context)==0x38,"EngineContext");
_Static_assert(offsetof(ft5955_winbio_pipeline,framework_interface)==0x48,"FrameworkInterface");
#endif
