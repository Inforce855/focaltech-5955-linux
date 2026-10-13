/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Address-keyed, recursive pthread mutexes for Win32 CRITICAL_SECTION API.
 * Internal mapping avoids writing foreign layout fields into the 40-byte
 * Windows structure. Assumes DLL accesses locks ONLY via Win32 functions;
 * direct accesses to LockCount/OwningThread remain an unverified ABI gap.
 *
 * Lock ownership is enforced by pthread mutexes. A deletion waits for
 * outstanding callers; deleting a lock while oneself holding it is invalid
 * (on Windows as well) and could deadlock. Misuse aborts in the isolated
 * harness rather than silently discarding critical section operations.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_cs.h"
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

struct cs_entry {
    void *address;
    pthread_mutex_t mutex;
    pthread_cond_t drained;
    unsigned active_users;
    int deleting;
    struct cs_entry *next;
};
static pthread_mutex_t map_lock = PTHREAD_MUTEX_INITIALIZER;
static struct cs_entry *entries;

static void invalid(const char *message)
{
    fprintf(stderr, "[5955 win32 cs] FATAL: %s\n", message);
    abort();
}
static struct cs_entry *lookup(void *address)
{
    for (struct cs_entry *e = entries; e; e = e->next)
        if (e->address == address)
            return e;
    return NULL;
}
void FT5955_CS_MS ft5955_InitializeCriticalSection(void *cs)
{
    if (!cs) invalid("InitializeCriticalSection(NULL)");
    struct cs_entry *e = calloc(1, sizeof(*e));
    if (!e) invalid("cannot allocate critical section");
    pthread_mutexattr_t attributes;
    if (pthread_mutexattr_init(&attributes) != 0) invalid("mutexattr init failed");
    if (pthread_mutexattr_settype(&attributes, PTHREAD_MUTEX_RECURSIVE) != 0)
        invalid("recursive mutex unavailable");
    if (pthread_mutex_init(&e->mutex, &attributes) != 0)
        invalid("mutex init failed");
    pthread_mutexattr_destroy(&attributes);
    if (pthread_cond_init(&e->drained, NULL) != 0)
        invalid("condition init failed");
    e->address = cs;
    pthread_mutex_lock(&map_lock);
    if (lookup(cs)) invalid("double initialization of critical section");
    e->next = entries;
    entries = e;
    pthread_mutex_unlock(&map_lock);
}
int FT5955_CS_MS
ft5955_InitializeCriticalSectionAndSpinCount(void *cs, uint32_t spin_count)
{
    (void)spin_count; /* Spin count only affects performance on Windows. */
    ft5955_InitializeCriticalSection(cs);
    return 1;
}
void FT5955_CS_MS ft5955_EnterCriticalSection(void *cs)
{
    pthread_mutex_lock(&map_lock);
    struct cs_entry *e = lookup(cs);
    if (!e || e->deleting) invalid("enter of unknown/deleting critical section");
    e->active_users++; /* Pins e during concurrent Delete, including waiters */
    pthread_mutex_unlock(&map_lock);
    if (pthread_mutex_lock(&e->mutex) != 0) invalid("enter mutex failed");
}
void FT5955_CS_MS ft5955_LeaveCriticalSection(void *cs)
{
    pthread_mutex_lock(&map_lock);
    struct cs_entry *e = lookup(cs);
    if (!e || !e->active_users) invalid("leave of unknown/unlocked critical section");
    /* pthread ownership validation must happen before dropping the pin. */
    if (pthread_mutex_unlock(&e->mutex) != 0)
        invalid("leave by non-owner of critical section");
    e->active_users--;
    if (!e->active_users && e->deleting)
        pthread_cond_signal(&e->drained);
    pthread_mutex_unlock(&map_lock);
}
void FT5955_CS_MS ft5955_DeleteCriticalSection(void *cs)
{
    pthread_mutex_lock(&map_lock);
    struct cs_entry *e = lookup(cs);
    if (!e || e->deleting) invalid("delete of unknown/deleting critical section");
    e->deleting = 1;
    while (e->active_users)
        pthread_cond_wait(&e->drained, &map_lock);
    struct cs_entry **link = &entries;
    while (*link != e) link = &(*link)->next;
    *link = e->next;
    pthread_mutex_unlock(&map_lock);
    if (pthread_mutex_destroy(&e->mutex) != 0)
        invalid("destroy of busy critical section");
    pthread_cond_destroy(&e->drained);
    free(e);
}
