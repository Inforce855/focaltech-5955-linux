/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Restricted Win32 environment-variable shim with detached snapshots.
 *
 * Deliberately limited to printable ASCII UTF-16 input. Windows ordinarily
 * accepts broader Unicode and drive-current-directory pseudo-variables;
 * reject unsupported input rather than guessing about name equivalence.
 * This private environment starts EMPTY, independent of the Linux process.
 * No host environment, filesystem or device accesses occur.
 *
 * GetEnvironmentStringsW returns a new independently owned snapshot. Only a
 * block previously returned by this module may be freed. Mutations leave
 * older snapshots unchanged. All registry operations are mutex-serialised.
 */
#include "ft5955_compat_env.h"
#include "ft5955_compat_error.h"
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { ERROR_INVALID_PARAMETER = 87, ERROR_NOT_ENOUGH_MEMORY = 8,
       ERROR_ENVVAR_NOT_FOUND = 203 };
enum { MAX_VARIABLES = 64, MAX_NAME = 127, MAX_VALUE = 4096 };
struct variable {
    uint16_t name[MAX_NAME+1];
    uint16_t *value;
    size_t name_length, value_length;
    struct variable *next;
};
struct snapshot {
    uint16_t *block;
    struct snapshot *next;
};
static pthread_mutex_t environment_lock = PTHREAD_MUTEX_INITIALIZER;
static struct variable *variables;
static struct snapshot *snapshots;
static unsigned variable_count;

static uint16_t folded(uint16_t c)
{
    return c >= 'a' && c <= 'z' ? (uint16_t)(c - ('a' - 'A')) : c;
}
static int case_compare(const uint16_t *a, const uint16_t *b)
{
    for (;;) {
        uint16_t x = folded(*a++), y = folded(*b++);
        if (x != y) return x < y ? -1 : 1;
        if (!x) return 0;
    }
}
static int length_checked(const uint16_t *input, size_t limit,
                          int is_name, size_t *out)
{
    if (!input) return 0;
    for (size_t i=0; i<=limit; ++i) {
        const uint16_t c=input[i];
        if (!c) {
            if (is_name && !i) return 0;
            *out=i;
            return 1;
        }
        if (c < 0x20u || c > 0x7eu || (is_name && c == '='))
            return 0;
    }
    return 0;
}
int FT5955_ENV_MS
ft5955_SetEnvironmentVariableW(const uint16_t *name, const uint16_t *value)
{
    size_t nlen=0, vlen=0;
    if (!length_checked(name, MAX_NAME, 1, &nlen) ||
        (value && !length_checked(value, MAX_VALUE, 0, &vlen))) {
        ft5955_SetLastError(ERROR_INVALID_PARAMETER);
        return 0;
    }
    pthread_mutex_lock(&environment_lock);
    struct variable **link=&variables;
    while (*link && case_compare((*link)->name,name)<0)
        link=&(*link)->next;
    struct variable *existing=(*link && !case_compare((*link)->name,name))
                                ? *link : NULL;
    if (!value) {
        if (!existing) {
            pthread_mutex_unlock(&environment_lock);
            ft5955_SetLastError(ERROR_ENVVAR_NOT_FOUND);
            return 0;
        }
        *link=existing->next;
        variable_count--;
        free(existing->value);
        free(existing);
        pthread_mutex_unlock(&environment_lock);
        return 1;
    }
    if (!existing && variable_count >= MAX_VARIABLES) {
        pthread_mutex_unlock(&environment_lock);
        ft5955_SetLastError(ERROR_NOT_ENOUGH_MEMORY);
        return 0;
    }
    uint16_t *copied=malloc((vlen+1)*sizeof(uint16_t));
    if (!copied) {
        pthread_mutex_unlock(&environment_lock);
        ft5955_SetLastError(ERROR_NOT_ENOUGH_MEMORY);
        return 0;
    }
    memcpy(copied,value,(vlen+1)*sizeof(uint16_t));
    if (existing) {
        free(existing->value);
        existing->value=copied;
        existing->value_length=vlen;
    } else {
        struct variable *entry=calloc(1,sizeof *entry);
        if (!entry) {
            free(copied);
            pthread_mutex_unlock(&environment_lock);
            ft5955_SetLastError(ERROR_NOT_ENOUGH_MEMORY);
            return 0;
        }
        memcpy(entry->name,name,(nlen+1)*sizeof(uint16_t));
        entry->name_length=nlen;
        entry->value=copied;
        entry->value_length=vlen;
        entry->next=*link;
        *link=entry;
        variable_count++;
    }
    pthread_mutex_unlock(&environment_lock);
    return 1;
}
uint16_t *FT5955_ENV_MS ft5955_GetEnvironmentStringsW(void)
{
    pthread_mutex_lock(&environment_lock);
    size_t units=variable_count ? 1 : 2;
    for (struct variable *e=variables;e;e=e->next)
        units+=e->name_length+1+e->value_length+1;
    if (units > SIZE_MAX/sizeof(uint16_t)) {
        pthread_mutex_unlock(&environment_lock);
        ft5955_SetLastError(ERROR_NOT_ENOUGH_MEMORY);
        return NULL;
    }
    uint16_t *block=calloc(units,sizeof(uint16_t));
    struct snapshot *record=malloc(sizeof *record);
    if (!block || !record) {
        free(block);
        free(record);
        pthread_mutex_unlock(&environment_lock);
        ft5955_SetLastError(ERROR_NOT_ENOUGH_MEMORY);
        return NULL;
    }
    size_t at=0;
    for (struct variable *e=variables;e;e=e->next) {
        memcpy(block+at,e->name,e->name_length*sizeof(uint16_t));
        at+=e->name_length;
        block[at++]='=';
        memcpy(block+at,e->value,e->value_length*sizeof(uint16_t));
        at+=e->value_length;
        at++; /* NUL separator (calloc) */
    }
    /* calloc supplied final NUL; empty environment gets two NULs. */
    record->block=block;
    record->next=snapshots;
    snapshots=record;
    pthread_mutex_unlock(&environment_lock);
    return block;
}
int FT5955_ENV_MS ft5955_FreeEnvironmentStringsW(uint16_t *block)
{
    pthread_mutex_lock(&environment_lock);
    struct snapshot **link=&snapshots;
    while (*link && (*link)->block!=block)
        link=&(*link)->next;
    if (!*link) {
        pthread_mutex_unlock(&environment_lock);
        ft5955_SetLastError(ERROR_INVALID_PARAMETER);
        return 0;
    }
    struct snapshot *record=*link;
    *link=record->next;
    free(record->block);
    free(record);
    pthread_mutex_unlock(&environment_lock);
    return 1;
}
