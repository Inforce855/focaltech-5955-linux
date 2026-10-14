/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Isolated x64 Win32 process-heap shim tests. No DLL or USB.
 * Test failures return nonzero with line number; never intentionally abort.
 */
#include "ft5955_compat_heap.h"
#include "ft5955_compat_error.h"
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>

static atomic_uint failures;
#define CHECK(expr) do { if (!(expr)) { \
    fprintf(stderr,"5955 heap synthetic test failed at line %d: %s\n",__LINE__,#expr); \
    atomic_fetch_add(&failures,1); \
} } while(0)

static void test_basic(void)
{
    void *heap=ft5955_GetProcessHeap();
    CHECK(heap!=NULL);
    CHECK(ft5955_GetProcessHeap()==heap);
    CHECK(ft5955_HeapValidate(heap,0,NULL)==1);
    unsigned char *p=ft5955_HeapAlloc(heap,FT5955_HEAP_ZERO_MEMORY,32);
    if (!p) { CHECK(p!=NULL); return; }
    CHECK(((uintptr_t)p & 15u)==0);
    CHECK(ft5955_HeapSize(heap,0,p)==32);
    CHECK(ft5955_HeapValidate(heap,0,p)==1);
    for(unsigned i=0;i<32;i++) CHECK(p[i]==0);
    memset(p,0x5a,32);

    /* In-place-only growth may fail without modifying the original. */
    ft5955_SetLastError(77);
    CHECK(ft5955_HeapReAlloc(heap,FT5955_HEAP_REALLOC_IN_PLACE_ONLY,p,8192)==NULL);
    CHECK(ft5955_GetLastError()==77);
    CHECK(ft5955_HeapSize(heap,0,p)==32);

    unsigned char *larger=ft5955_HeapReAlloc(heap,FT5955_HEAP_ZERO_MEMORY,p,128);
    if (!larger) { CHECK(larger!=NULL); CHECK(ft5955_HeapFree(heap,0,p)); return; }
    CHECK(ft5955_HeapSize(heap,0,larger)==128);
    CHECK(((uintptr_t)larger&15u)==0);
    for(unsigned i=0;i<32;i++) CHECK(larger[i]==0x5a);
    for(unsigned i=32;i<128;i++) CHECK(larger[i]==0);
    CHECK(ft5955_HeapValidate(heap,0,p)==(p==larger?1:0));

    CHECK(ft5955_HeapReAlloc(heap,FT5955_HEAP_REALLOC_IN_PLACE_ONLY,
                            larger,64)==larger);
    CHECK(ft5955_HeapSize(heap,0,larger)==64);
    CHECK(ft5955_HeapReAlloc(heap,FT5955_HEAP_ZERO_MEMORY |
                            FT5955_HEAP_REALLOC_IN_PLACE_ONLY,
                            larger,96)==larger);
    CHECK(ft5955_HeapSize(heap,0,larger)==96);
    CHECK(ft5955_HeapFree(heap,0,larger)==1);
    CHECK(ft5955_HeapValidate(heap,0,larger)==0);
    CHECK(ft5955_HeapSize(heap,0,larger)==UINT64_MAX);
    CHECK(ft5955_HeapFree(heap,0,larger)==0);
    CHECK(ft5955_GetLastError()==87);
    CHECK(ft5955_HeapFree(heap,0,NULL)==1);
}
static void test_invalid(void)
{
    void *heap=ft5955_GetProcessHeap();
    void *wrong=(void*)(uintptr_t)0xdeadbeef;
    ft5955_SetLastError(123);
    CHECK(ft5955_HeapAlloc(wrong,0,10)==NULL);
    CHECK(ft5955_GetLastError()==123); /* allocation failure leaves it untouched */
    CHECK(ft5955_HeapAlloc(heap,4,10)==NULL); /* exceptions unsupported */
    CHECK(ft5955_HeapAlloc(heap,1,10)==NULL); /* NO_SERIALIZE unsupported */
    CHECK(ft5955_HeapAlloc(heap,0,UINT64_MAX)==NULL);
    CHECK(ft5955_GetLastError()==123);
    CHECK(ft5955_HeapSize(wrong,0,wrong)==UINT64_MAX);
    CHECK(ft5955_HeapSize(heap,1,wrong)==UINT64_MAX);
    CHECK(ft5955_HeapValidate(wrong,0,NULL)==0);
    CHECK(ft5955_HeapValidate(heap,0,wrong)==0);
    CHECK(ft5955_GetLastError()==123);
    CHECK(ft5955_HeapFree(wrong,0,wrong)==0);
    CHECK(ft5955_GetLastError()==6);
    CHECK(ft5955_HeapReAlloc(heap,0,wrong,12)==NULL);
    CHECK(ft5955_GetLastError()==6);
    CHECK(ft5955_HeapFree(heap,1,NULL)==0);
    CHECK(ft5955_GetLastError()==87);
}
static void test_query(void)
{
    void *heap=ft5955_GetProcessHeap();
    uint32_t result=0xdeadbeef;
    uint64_t returned=0;
    CHECK(ft5955_HeapQueryInformation(heap,0,&result,4,&returned)==1);
    CHECK(result==0 && returned==4);
    CHECK(ft5955_HeapQueryInformation(heap,0,NULL,0,&returned)==0);
    CHECK(returned==4);
    CHECK(ft5955_HeapQueryInformation(heap,1,&result,4,&returned)==0);
    CHECK(ft5955_HeapQueryInformation((void*)1,0,&result,4,&returned)==0);
    CHECK(ft5955_GetLastError()==6);
}
static void *worker(void *data)
{
    (void)data;
    void *heap=ft5955_GetProcessHeap();
    for(int i=0;i<3000;i++){
        unsigned char *p=ft5955_HeapAlloc(heap,FT5955_HEAP_ZERO_MEMORY,48);
        if(!p){CHECK(p!=NULL);return NULL;}
        CHECK(ft5955_HeapSize(heap,0,p)==48);
        CHECK(ft5955_HeapValidate(heap,0,p)==1);
        p[0]=(unsigned char)i;
        CHECK(ft5955_HeapFree(heap,0,p)==1);
    }
    return NULL;
}
int main(void)
{
    test_basic();
    test_invalid();
    test_query();
    pthread_t workers[4];
    int created=0;
    for(int i=0;i<4;i++){
        if(pthread_create(&workers[i],NULL,worker,NULL)!=0){
            CHECK(0);break;
        }
        created++;
    }
    for(int i=0;i<created;i++) CHECK(pthread_join(workers[i],NULL)==0);
    if(atomic_load(&failures)){
        fprintf(stderr,"5955 Win32 process heap: %u test failures\n",
                atomic_load(&failures));
        return 1;
    }
    puts("5955 tracked Win32 process heap: synthetic tests OK");
    return 0;
}
