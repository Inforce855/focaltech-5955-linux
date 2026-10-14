/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Offline virtual registry integration tests. No DLL, files or biometrics.
 * Test failures print source lines; no assertion-triggered core dumps.
 */
#include "ft5955_compat_registry.h"
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>
enum { SUCCESS=0, FILE_NOT_FOUND=2, ACCESS_DENIED=5,
       INVALID_HANDLE=6, INVALID_PARAMETER=87, MORE_DATA=234 };
static atomic_uint failures;
#define CHECK(expr) do {if(!(expr)){ \
    fprintf(stderr,"5955 virtual registry test line %d: %s\n",__LINE__,#expr); \
    atomic_fetch_add(&failures,1); \
}}while(0)

static void *thread_writer(void *user)
{
    unsigned index=(unsigned)(uintptr_t)user;
    char name[24];
    snprintf(name,sizeof name,"Worker%u",index);
    const uint32_t number=index+0x1234u;
    CHECK(ft5955_RegSetKeyValueA(FT5955_HKEY_CURRENT_USER,
          "Software\\FocalTech",name,FT5955_REG_DWORD,
          &number,sizeof number)==SUCCESS);
    void *handle=NULL;
    CHECK(ft5955_RegOpenKeyExA(FT5955_HKEY_CURRENT_USER,
          "Software\\FocalTech",0,FT5955_KEY_READ,&handle)==SUCCESS);
    if(handle){
        uint32_t actual=0,size=sizeof actual,type=0;
        CHECK(ft5955_RegQueryValueExA(handle,name,NULL,&type,
             (unsigned char *)&actual,&size)==SUCCESS);
        CHECK(size==4 && type==FT5955_REG_DWORD && actual==number);
        CHECK(ft5955_RegCloseKey(handle)==SUCCESS);
    }
    return NULL;
}
int main(void)
{
    void *handle=(void *)(uintptr_t)0xaaa;
    uint32_t status=ft5955_RegOpenKeyExA(
        FT5955_HKEY_CURRENT_USER,"Software\\FocalTech",
        0,FT5955_KEY_READ,&handle);
    CHECK(status==FILE_NOT_FOUND);
    CHECK(handle==(void *)(uintptr_t)0xaaa); /* failure leaves out untouched */
    const char tiger[]="Tiger";
    CHECK(ft5955_RegSetKeyValueA(FT5955_HKEY_CURRENT_USER,
          "Software\\FocalTech","Name",FT5955_REG_SZ,
          tiger,(uint32_t)sizeof tiger)==SUCCESS);
    CHECK(ft5955_RegOpenKeyExA(FT5955_HKEY_CURRENT_USER,
          "Software",0,FT5955_KEY_READ,&handle)==SUCCESS);
    if(handle && handle!=(void *)(uintptr_t)0xaaa)
        CHECK(ft5955_RegCloseKey(handle)==SUCCESS);
    handle=NULL;
    CHECK(ft5955_RegOpenKeyExA(FT5955_HKEY_CURRENT_USER,
          "software\\focalTECH",0,FT5955_KEY_READ,&handle)==SUCCESS);
    if(handle){
        uint32_t length=0,type=0;
        CHECK(ft5955_RegQueryValueExA(handle,"nAmE",NULL,
             &type,NULL,&length)==SUCCESS);
        CHECK(type==FT5955_REG_SZ && length==sizeof tiger);
        unsigned char small[2]={0x77,0x77};
        length=sizeof small;
        CHECK(ft5955_RegQueryValueExA(handle,"Name",NULL,
             &type,small,&length)==MORE_DATA);
        CHECK(length==sizeof tiger && small[0]==0x77 && small[1]==0x77);
        unsigned char actual[16]={0};
        length=sizeof actual;
        CHECK(ft5955_RegQueryValueExA(handle,"NAME",NULL,
             &type,actual,&length)==SUCCESS);
        CHECK(length==sizeof tiger && strcmp((char *)actual,tiger)==0);
        CHECK(ft5955_RegQueryValueExA(handle,"Absent",NULL,
             &type,NULL,&length)==FILE_NOT_FOUND);
        CHECK(ft5955_RegQueryValueExA(handle,"Name",&type,
             &type,NULL,&length)==INVALID_PARAMETER);
        CHECK(ft5955_RegQueryValueExA(handle,"Name",NULL,
             &type,actual,NULL)==INVALID_PARAMETER);
        CHECK(ft5955_RegSetKeyValueA(handle,NULL,"Write",
             FT5955_REG_DWORD,&type,sizeof type)==ACCESS_DENIED);
        void *elevated=(void *)(uintptr_t)0xaaa;
        CHECK(ft5955_RegOpenKeyExA(handle,NULL,0,
              FT5955_KEY_SET_VALUE,&elevated)==ACCESS_DENIED);
        CHECK(elevated==(void *)(uintptr_t)0xaaa);
        CHECK(ft5955_RegCloseKey(handle)==SUCCESS);
        CHECK(ft5955_RegCloseKey(handle)==INVALID_HANDLE);
        CHECK(ft5955_RegQueryValueExA(handle,"Name",NULL,
             &type,NULL,&length)==INVALID_HANDLE);
    }
    void *writer=NULL;
    CHECK(ft5955_RegOpenKeyExA(FT5955_HKEY_CURRENT_USER,
          "Software\\FocalTech",0,FT5955_KEY_WRITE,&writer)==SUCCESS);
    if(writer){
        const uint32_t number=0x12345678u;
        CHECK(ft5955_RegSetKeyValueA(writer,NULL,"Number",
              FT5955_REG_DWORD,&number,4)==SUCCESS);
        CHECK(ft5955_RegQueryValueExA(writer,"Number",NULL,
              NULL,NULL,NULL)==ACCESS_DENIED);
        CHECK(ft5955_RegCloseKey(writer)==SUCCESS);
    }
    void *reader=NULL;
    CHECK(ft5955_RegOpenKeyExA(FT5955_HKEY_CURRENT_USER,
          "Software\\FocalTech",0,FT5955_KEY_QUERY_VALUE,&reader)==SUCCESS);
    if(reader){
        uint32_t n=0,type=0,size=sizeof n;
        CHECK(ft5955_RegQueryValueExA(reader,"nUmBeR",NULL,
              &type,(unsigned char*)&n,&size)==SUCCESS);
        CHECK(n==0x12345678u && size==4 && type==FT5955_REG_DWORD);
        CHECK(ft5955_RegCloseKey(reader)==SUCCESS);
    }
    CHECK(ft5955_RegSetKeyValueA(FT5955_HKEY_CURRENT_USER,NULL,
          "Invalid",FT5955_REG_DWORD,NULL,4)==INVALID_PARAMETER);
    CHECK(ft5955_RegSetKeyValueA(FT5955_HKEY_CURRENT_USER,NULL,
          "Invalid",FT5955_REG_SZ,"not-terminated",4)==INVALID_PARAMETER);
    CHECK(ft5955_RegOpenKeyExA(NULL,"Software",0,
          FT5955_KEY_READ,&reader)==INVALID_HANDLE);
    CHECK(ft5955_RegOpenKeyExA(FT5955_HKEY_CURRENT_USER,
          "Software",1,FT5955_KEY_READ,&reader)==INVALID_PARAMETER);
    CHECK(ft5955_RegCloseKey(FT5955_HKEY_LOCAL_MACHINE)==SUCCESS);
    CHECK(ft5955_RegCloseKey((void *)(uintptr_t)0x333)==INVALID_HANDLE);
    void *same=NULL;
    CHECK(ft5955_RegOpenKeyExA(FT5955_HKEY_CURRENT_USER,
          NULL,0,FT5955_KEY_READ,&same)==SUCCESS);
    CHECK(same==FT5955_HKEY_CURRENT_USER);

    pthread_t threads[4];
    int started=0;
    for(unsigned i=0;i<4;i++){
        if(pthread_create(&threads[i],NULL,thread_writer,
                          (void *)(uintptr_t)i)!=0){CHECK(0);break;}
        started++;
    }
    for(int i=0;i<started;i++) CHECK(pthread_join(threads[i],NULL)==0);
    if(atomic_load(&failures)){
        fprintf(stderr,"5955 virtual registry: %u test failures\n",
                atomic_load(&failures)); return 1;
    }
    puts("5955 isolated Windows ANSI registry: synthetic tests OK");
    return 0;
}
