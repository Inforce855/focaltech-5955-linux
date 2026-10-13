/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Inert x64 SList ABI regression test; NO proprietary DLL, USB or biometrics.
 * Errors return nonzero instead of aborting.
 */
#include "ft5955_compat_slist.h"
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { WORKERS=4, PER_WORKER=1500, COUNT=WORKERS*PER_WORKER };
struct item {
    ft5955_slist_entry link;
    uint32_t serial;
};
static ft5955_slist_header head;
static struct item entries[COUNT];
static unsigned char visited[COUNT];
static unsigned failures;
#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr,"5955 SLIST test line %d: %s\n", __LINE__, #expr); \
    __atomic_fetch_add(&failures,1,__ATOMIC_RELAXED); \
} } while(0)

static void *push_worker(void *arg)
{
    const size_t id=(size_t)(uintptr_t)arg;
    for (size_t i=0;i<PER_WORKER;i++) {
        size_t ix=id*PER_WORKER+i;
        entries[ix].serial=(uint32_t)ix;
        (void)ft5955_InterlockedPushEntrySList(&head,&entries[ix].link);
    }
    return NULL;
}
int main(void)
{
    CHECK(sizeof(ft5955_slist_header)==16);
    CHECK(sizeof(ft5955_slist_entry)==16);
    CHECK(((uintptr_t)&head & 15u)==0);
    CHECK(((uintptr_t)&entries[0].link & 15u)==0);

    ft5955_InitializeSListHead(&head);
    CHECK(head.depth_sequence==0 && head.next_region==0);
    struct item first={{NULL}, 20}, second={{NULL}, 21};
    CHECK(ft5955_InterlockedPushEntrySList(&head,&first.link)==NULL);
    CHECK(ft5955_InterlockedPushEntrySList(&head,&second.link)==&first.link);
    CHECK((head.depth_sequence & 0xffffu)==2);
    CHECK(head.next_region==(uintptr_t)&second.link);
    CHECK(ft5955_InterlockedFlushSList(&head)==&second.link);
    CHECK(second.link.Next==&first.link);
    CHECK(first.link.Next==NULL);
    CHECK(ft5955_InterlockedFlushSList(&head)==NULL);
    CHECK((head.depth_sequence & 0xffffu)==0);
    CHECK(head.next_region==0);

    ft5955_InitializeSListHead(&head);
    pthread_t threads[WORKERS];
    int started=0;
    for(int i=0;i<WORKERS;i++) {
        if(pthread_create(&threads[i],NULL,push_worker,(void*)(uintptr_t)i)) {
            CHECK(0); break;
        }
        started++;
    }
    for(int i=0;i<started;i++) CHECK(!pthread_join(threads[i],NULL));
    if(started==WORKERS) {
        CHECK((head.depth_sequence & 0xffffu)==COUNT);
        ft5955_slist_entry *node=ft5955_InterlockedFlushSList(&head);
        unsigned count=0;
        memset(visited,0,sizeof visited);
        /* link is the first member, so its pointer identifies struct item. */
        while(node && count<=COUNT) {
            const struct item *entry=(const struct item *)node;
            uint32_t ix=entry->serial;
            CHECK(ix<COUNT);
            if(ix<COUNT) {
                CHECK(visited[ix]==0);
                visited[ix]=1;
            }
            node=node->Next;
            count++;
        }
        CHECK(node==NULL);
        CHECK(count==COUNT);
        for(unsigned i=0;i<COUNT;i++) CHECK(visited[i]==1);
        CHECK(head.next_region==0);
        CHECK((head.depth_sequence & 0xffffu)==0);
    }
    if(__atomic_load_n(&failures,__ATOMIC_RELAXED)) {
        fprintf(stderr,"5955 x64 SLIST: %u synthetic test failures\n",
                __atomic_load_n(&failures,__ATOMIC_RELAXED));
        return 1;
    }
    puts("5955 x64 atomic SLIST push/flush: synthetic tests OK");
    return 0;
}
