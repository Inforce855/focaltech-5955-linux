/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic Win32 ID and TEB.ClientId test; no DLL/USB/biometric access.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_identity.h"
#include "ft5955_compat_teb_layout.h"
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static uint32_t tids[3], pids[3];
static const uint8_t *tebs[3];
static pthread_barrier_t barrier;
static int failures;
#define CHECK(x) do { if (!(x)) { \
    fprintf(stderr,"5955 identity test line %d: %s\n", __LINE__, #x); \
    __atomic_fetch_add(&failures,1,__ATOMIC_RELAXED); \
} } while (0)

static uint64_t get64(const uint8_t *base, unsigned offset)
{
    uint64_t v=0;
    if (base) memcpy(&v,base+offset,sizeof v);
    return v;
}
static void inspect_thread(int index)
{
    pids[index]=ft5955_GetCurrentProcessId();
    tids[index]=ft5955_GetCurrentThreadId();
    CHECK(pids[index] != 0);
    CHECK(tids[index] != 0);
    CHECK(pids[index] == (uint32_t)getpid());
    CHECK(ft5955_GetCurrentThreadId() == tids[index]);
    CHECK(ft5955_teb_prepare_current() == 0);
    tebs[index]=ft5955_teb_view_current();
    CHECK(tebs[index] != NULL);
    CHECK(get64(tebs[index],0x40) == pids[index]);
    CHECK(get64(tebs[index],0x48) == tids[index]);
    CHECK(ft5955_teb_prepare_current() == 0);
    CHECK(ft5955_GetCurrentThreadId() == tids[index]);
    CHECK(get64(tebs[index],0x48) == tids[index]);
}
static void *worker(void *arg)
{
    inspect_thread((int)(uintptr_t)arg);
    int b=pthread_barrier_wait(&barrier);
    CHECK(b == 0 || b == PTHREAD_BARRIER_SERIAL_THREAD);
    b=pthread_barrier_wait(&barrier);
    CHECK(b == 0 || b == PTHREAD_BARRIER_SERIAL_THREAD);
    return NULL;
}
int main(void)
{
    if (pthread_barrier_init(&barrier,NULL,3)!=0) return 2;
    pthread_t a,b;
    if (pthread_create(&a,NULL,worker,(void*)(uintptr_t)1)!=0) return 2;
    if (pthread_create(&b,NULL,worker,(void*)(uintptr_t)2)!=0) return 2;
    inspect_thread(0);
    int rc=pthread_barrier_wait(&barrier);
    CHECK(rc == 0 || rc == PTHREAD_BARRIER_SERIAL_THREAD);
    for (int i=0;i<3;i++) {
        CHECK(pids[i] == pids[0]);
        for (int j=i+1;j<3;j++) {
            CHECK(tids[i] != tids[j]);
            CHECK(tebs[i] != tebs[j]);
        }
    }
    rc=pthread_barrier_wait(&barrier);
    CHECK(rc == 0 || rc == PTHREAD_BARRIER_SERIAL_THREAD);
    CHECK(pthread_join(a,NULL)==0);
    CHECK(pthread_join(b,NULL)==0);
    CHECK(pthread_barrier_destroy(&barrier)==0);
    if (failures) {
        fprintf(stderr,"5955 Win32 IDs: %d synthetic test failures\n",failures);
        return 1;
    }
    puts("5955 process/thread IDs and TEB.ClientId: synthetic tests OK");
    return 0;
}
