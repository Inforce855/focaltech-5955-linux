/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Standalone virtual Win32 environment tests. No PE code, USB or biometrics.
 * Failures are reported rather than aborting or producing core dumps.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_env.h"
#include "ft5955_compat_error.h"
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static atomic_uint failures;
#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr,"5955 virtual env test line %d: %s\n", __LINE__, #expr); \
    atomic_fetch_add(&failures,1); \
} } while (0)
static const uint16_t foo[]={'F','o','o',0};
static const uint16_t foo_lower[]={'f','O','O',0};
static const uint16_t alpha[]={'A','L','P','H','A',0};
static const uint16_t bar[]={'B','a','r',0};
static const uint16_t baz[]={'B','a','z',0};
static const uint16_t empty[]={0};
static const uint16_t invalid_name[]={'b','a','d','=','x',0};
static const uint16_t invalid_utf16[]={'N',0x0100u,0};
static const uint16_t host_name[]={'F','T','5','9','5','5','_','N','O','_','H','O','S','T',0};
static const uint16_t host_value[]={'S','a','f','e',0};

static int ascii_equals(const uint16_t *actual, const char *expected)
{
    for (size_t i=0;;++i) {
        if (actual[i] != (unsigned char)expected[i]) return 0;
        if (!expected[i]) return 1;
    }
}
static size_t next_string(const uint16_t *p)
{
    size_t n=0;
    while (p[n] && n<5000) n++;
    return n;
}
static void *worker(void *arg)
{
    static const uint16_t *keys[4] = {
        (const uint16_t[]){'W','O','R','K','E','R','1',0},
        (const uint16_t[]){'W','O','R','K','E','R','2',0},
        (const uint16_t[]){'W','O','R','K','E','R','3',0},
        (const uint16_t[]){'W','O','R','K','E','R','4',0}
    };
    const size_t idx=(size_t)(uintptr_t)arg;
    CHECK(ft5955_SetEnvironmentVariableW(keys[idx],host_value));
    uint16_t *snapshot=ft5955_GetEnvironmentStringsW();
    CHECK(snapshot!=NULL);
    if (snapshot) CHECK(ft5955_FreeEnvironmentStringsW(snapshot));
    return NULL;
}
int main(void)
{
    const char *before_host=getenv("FT5955_NO_HOST");
    uint16_t *start=ft5955_GetEnvironmentStringsW();
    CHECK(start != NULL);
    if (start) {
        CHECK(start[0]==0 && start[1]==0);
        CHECK(ft5955_FreeEnvironmentStringsW(start));
        CHECK(!ft5955_FreeEnvironmentStringsW(start));
        CHECK(ft5955_GetLastError()==87);
    }
    CHECK(ft5955_SetEnvironmentVariableW(foo,bar));
    CHECK(ft5955_SetEnvironmentVariableW(alpha,baz));
    uint16_t *old=ft5955_GetEnvironmentStringsW();
    CHECK(old != NULL);
    if (old) {
        size_t n=next_string(old);
        CHECK(ascii_equals(old,"ALPHA=Baz"));
        CHECK(ascii_equals(old+n+1,"Foo=Bar"));
        CHECK(old[n+1+next_string(old+n+1)+1]==0);
    }
    CHECK(ft5955_SetEnvironmentVariableW(foo_lower,baz));
    uint16_t *updated=ft5955_GetEnvironmentStringsW();
    CHECK(updated != NULL);
    if (updated) {
        size_t n=next_string(updated);
        CHECK(ascii_equals(updated+n+1,"Foo=Baz"));
        CHECK(ft5955_FreeEnvironmentStringsW(updated));
    }
    if (old) {
        size_t n=next_string(old);
        CHECK(ascii_equals(old+n+1,"Foo=Bar")); /* snapshot independent */
        CHECK(ft5955_FreeEnvironmentStringsW(old));
    }
    CHECK(ft5955_SetEnvironmentVariableW(foo,empty));
    uint16_t *blank=ft5955_GetEnvironmentStringsW();
    CHECK(blank != NULL);
    if (blank) {
        size_t n=next_string(blank);
        CHECK(ascii_equals(blank+n+1,"Foo="));
        CHECK(ft5955_FreeEnvironmentStringsW(blank));
    }
    CHECK(ft5955_SetEnvironmentVariableW(foo,NULL));
    CHECK(!ft5955_SetEnvironmentVariableW(foo,NULL));
    CHECK(ft5955_GetLastError()==203);
    CHECK(!ft5955_SetEnvironmentVariableW(NULL,baz));
    CHECK(ft5955_GetLastError()==87);
    CHECK(!ft5955_SetEnvironmentVariableW(invalid_name,baz));
    CHECK(!ft5955_SetEnvironmentVariableW(invalid_utf16,baz));
    CHECK(ft5955_SetEnvironmentVariableW(host_name,host_value));
    const char *after_host=getenv("FT5955_NO_HOST");
    CHECK((before_host==NULL && after_host==NULL) ||
          (before_host && after_host && strcmp(before_host,after_host)==0));
    CHECK(ft5955_SetEnvironmentVariableW(host_name,NULL));
    CHECK(!ft5955_FreeEnvironmentStringsW(NULL));
    CHECK(ft5955_GetLastError()==87);

    pthread_t threads[4];
    int created=0;
    for (int i=0;i<4;i++) {
        if (pthread_create(&threads[i],NULL,worker,(void*)(uintptr_t)i)!=0) {
            CHECK(0); break;
        }
        created++;
    }
    for (int i=0;i<created;i++) CHECK(pthread_join(threads[i],NULL)==0);
    uint16_t *all=ft5955_GetEnvironmentStringsW();
    CHECK(all!=NULL);
    if (all) {
        unsigned entries=0;
        for (size_t offset=0;all[offset] && offset<65536;) {
            entries++;
            offset+=next_string(all+offset)+1;
        }
        CHECK(entries==5); /* ALPHA plus four worker entries */
        CHECK(ft5955_FreeEnvironmentStringsW(all));
    }
    if (atomic_load(&failures)) {
        fprintf(stderr,"5955 virtual Windows environment: %u failures\n",
                atomic_load(&failures));
        return 1;
    }
    puts("5955 isolated Win32 environment and snapshots: synthetic tests OK");
    return 0;
}
