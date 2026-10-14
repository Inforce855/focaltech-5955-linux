/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Restricted and bounded, entirely private Win32 ANSI registry.
 * Missing keys return ERROR_FILE_NOT_FOUND; RegSetKeyValueA creates
 * private keys and values under the supplied predefined or opened key.
 * Dynamic HKEYs are generation-tagged integers, NEVER dereferenced.
 *
 * Does not seed any real Windows configuration, support non-ASCII ANSI
 * code pages, persistent storage, permissions/ACLs, WOW64 views, remote
 * registry, notifications, or any host-registry integration. The
 * predefined HKCU/HKLM roots are virtual and initially empty.
 */
#include "ft5955_compat_registry.h"
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

enum { ERROR_SUCCESS = 0, ERROR_FILE_NOT_FOUND = 2,
       ERROR_ACCESS_DENIED = 5, ERROR_INVALID_HANDLE = 6,
       ERROR_NOT_ENOUGH_MEMORY = 8, ERROR_INVALID_PARAMETER = 87,
       ERROR_MORE_DATA = 234 };
enum { MAX_KEYS = 128, MAX_VALUES = 256, MAX_HANDLES = 128,
       MAX_PATH = 255, MAX_NAME = 127, MAX_DATA = 4096 };
#define HANDLE_TAG UINT64_C(0x5955000000000000)
struct key_item { uint32_t root; char path[MAX_PATH+1]; };
struct value_item {
    unsigned key_index;
    char name[MAX_NAME+1];
    uint32_t type, length;
    unsigned char bytes[MAX_DATA];
};
struct open_handle {
    uint32_t generation, access, root;
    unsigned active;
    char path[MAX_PATH+1];
};
struct location {
    uint32_t root, access;
    char path[MAX_PATH+1];
};
static pthread_mutex_t registry_lock = PTHREAD_MUTEX_INITIALIZER;
static struct key_item keys[MAX_KEYS];
static struct value_item values[MAX_VALUES];
static struct open_handle handles[MAX_HANDLES];
static unsigned nkeys, nvalues;

static char fold_ascii(char c)
{
    return (c >= 'A' && c <= 'Z') ? (char)(c + ('a'-'A')) : c;
}
static int normalise(char *out, size_t capacity, const char *src,
                     int allow_backslash)
{
    if (!src) { *out=0; return 1; }
    size_t i=0;
    for (; i<capacity; i++) {
        unsigned char c=(unsigned char)src[i];
        if (!c) {
            if (i && allow_backslash && out[i-1]=='\\') return 0;
            out[i]=0; return 1;
        }
        if (c<0x20 || c>0x7e || c=='=' ||
            (!allow_backslash && c=='\\') ||
            (allow_backslash && c=='\\' &&
             (!i || (i && out[i-1]=='\\'))))
            return 0;
        out[i]=fold_ascii((char)c);
    }
    return 0; /* too long or no terminator within limit */
}
static int key_path(char *out, const char *base, const char *part)
{
    char normal[MAX_PATH+1];
    if (!normalise(normal, sizeof normal, part, 1)) return 0;
    size_t n=strlen(base), m=strlen(normal);
    if (n+m+(n&&m?1u:0u)>MAX_PATH) return 0;
    memcpy(out,base,n);
    if(n&&m) out[n++]='\\';
    memcpy(out+n,normal,m+1);
    return 1;
}
static int predefined(void *hkey, uint32_t *root)
{
    uint64_t raw=(uint64_t)(uintptr_t)hkey;
    /* Windows predefined HKEY constants can be sign- or zero-extended. */
    if ((raw >> 32) != 0 && (raw >> 32) != UINT32_MAX)
        return 0;
    uint32_t value=(uint32_t)raw;
    if (value<0x80000000u || value>0x80000005u || value==0x80000004u)
        return 0; /* performance-data root unsupported */
    *root=value;
    return 1;
}
static struct open_handle *find_handle(void *h)
{
    uint64_t raw=(uint64_t)(uintptr_t)h;
    if ((raw & UINT64_C(0xffff000000000000)) != HANDLE_TAG)
        return NULL;
    uint32_t slot=(uint32_t)(raw & 0xffffu);
    uint32_t generation=(uint32_t)((raw >> 16) & UINT32_MAX);
    if (!slot || slot>MAX_HANDLES) return NULL;
    struct open_handle *entry=&handles[slot-1];
    return entry->active && entry->generation==generation ? entry:NULL;
}
static int location_of(void *h, struct location *at)
{
    uint32_t root=0;
    if (predefined(h,&root)) {
        at->root=root; at->path[0]=0; at->access=UINT32_MAX;
        return 1;
    }
    struct open_handle *open=find_handle(h);
    if (!open) return 0;
    at->root=open->root;
    at->access=open->access;
    strcpy(at->path,open->path);
    return 1;
}
static int lookup_key(uint32_t root, const char *path)
{
    for (unsigned i=0;i<nkeys;i++)
        if(keys[i].root==root && !strcmp(keys[i].path,path))
            return (int)i;
    return -1;
}
static int add_key(uint32_t root, const char *path)
{
    int existing=lookup_key(root,path);
    if (existing>=0) return existing;
    if (nkeys==MAX_KEYS) return -1;
    unsigned index=nkeys++;
    keys[index].root=root;
    strcpy(keys[index].path,path);
    return (int)index;
}
static int create_path(uint32_t root, const char *path)
{
    char prefix[MAX_PATH+1];
    const size_t length=strlen(path);
    /* Create path prefixes too, like the nested subkeys created by Windows. */
    if (add_key(root,"")<0) return -1;
    for(size_t i=0;i<length;i++) {
        if(path[i]!='\\') continue;
        memcpy(prefix,path,i);
        prefix[i]=0;
        if(add_key(root,prefix)<0) return -1;
    }
    return add_key(root,path);
}
static int lookup_value(unsigned key_index, const char *name)
{
    for (unsigned i=0;i<nvalues;i++)
        if(values[i].key_index==key_index &&
           !strcmp(values[i].name,name)) return (int)i;
    return -1;
}
uint32_t FT5955_REG_MS ft5955_RegOpenKeyExA(
    void *hkey, const char *subkey, uint32_t options,
    uint32_t access, void **result)
{
    if (!result || options || (access & ~0x000f003fu))
        return ERROR_INVALID_PARAMETER;
    pthread_mutex_lock(&registry_lock);
    struct location from;
    if (!location_of(hkey,&from)) {
        pthread_mutex_unlock(&registry_lock); return ERROR_INVALID_HANDLE;
    }
    /* In this ACL-free virtual registry, a child open cannot grant more
     * query/set-value rights than the supplied non-predefined parent. */
    uint32_t predefined_root=0;
    if (!predefined(hkey,&predefined_root) &&
        ((access & (FT5955_KEY_QUERY_VALUE | FT5955_KEY_SET_VALUE)) &
         ~from.access)) {
        pthread_mutex_unlock(&registry_lock); return ERROR_ACCESS_DENIED;
    }
    char path[MAX_PATH+1];
    if (!key_path(path,from.path,subkey)) {
        pthread_mutex_unlock(&registry_lock); return ERROR_INVALID_PARAMETER;
    }
    if (lookup_key(from.root,path)<0 &&
        !(path[0]==0 && predefined(hkey,&from.root))) {
        pthread_mutex_unlock(&registry_lock); return ERROR_FILE_NOT_FOUND;
    }
    /* Opening the root of a predefined HKEY returns that same root. */
    if (!path[0] && predefined(hkey,&from.root)) {
        *result=hkey;
        pthread_mutex_unlock(&registry_lock); return ERROR_SUCCESS;
    }
    for(unsigned i=0;i<MAX_HANDLES;i++) {
        if (handles[i].active) continue;
        struct open_handle *h=&handles[i];
        if (++h->generation==0) h->generation=1;
        h->root=from.root; h->access=access; h->active=1;
        strcpy(h->path,path);
        *result=(void *)(uintptr_t)(HANDLE_TAG |
                  ((uint64_t)h->generation<<16) | (uint64_t)(i+1));
        pthread_mutex_unlock(&registry_lock); return ERROR_SUCCESS;
    }
    pthread_mutex_unlock(&registry_lock); return ERROR_NOT_ENOUGH_MEMORY;
}
uint32_t FT5955_REG_MS ft5955_RegQueryValueExA(
    void *hkey, const char *value_name, uint32_t *reserved,
    uint32_t *type, unsigned char *data, uint32_t *data_bytes)
{
    if (reserved || (data && !data_bytes)) return ERROR_INVALID_PARAMETER;
    char name[MAX_NAME+1];
    if (!normalise(name,sizeof name,value_name,0)) return ERROR_INVALID_PARAMETER;
    pthread_mutex_lock(&registry_lock);
    struct location at;
    if (!location_of(hkey,&at)) {
        pthread_mutex_unlock(&registry_lock); return ERROR_INVALID_HANDLE;
    }
    if (!(at.access & FT5955_KEY_QUERY_VALUE)) {
        pthread_mutex_unlock(&registry_lock); return ERROR_ACCESS_DENIED;
    }
    int key=lookup_key(at.root,at.path);
    int index=key<0 ? -1 : lookup_value((unsigned)key,name);
    if (index<0) {
        pthread_mutex_unlock(&registry_lock); return ERROR_FILE_NOT_FOUND;
    }
    const struct value_item *value=&values[index];
    if (type) *type=value->type;
    if (data_bytes) {
        uint32_t capacity=*data_bytes;
        *data_bytes=value->length;
        if (data && capacity<value->length) {
            pthread_mutex_unlock(&registry_lock); return ERROR_MORE_DATA;
        }
    }
    if(data && value->length) memcpy(data,value->bytes,value->length);
    pthread_mutex_unlock(&registry_lock); return ERROR_SUCCESS;
}
uint32_t FT5955_REG_MS ft5955_RegCloseKey(void *hkey)
{
    uint32_t root;
    if (predefined(hkey,&root)) return ERROR_SUCCESS;
    pthread_mutex_lock(&registry_lock);
    struct open_handle *h=find_handle(hkey);
    if (!h) {
        pthread_mutex_unlock(&registry_lock); return ERROR_INVALID_HANDLE;
    }
    h->active=0; h->path[0]=0; h->access=0;
    pthread_mutex_unlock(&registry_lock); return ERROR_SUCCESS;
}
uint32_t FT5955_REG_MS ft5955_RegSetKeyValueA(
    void *hkey, const char *subkey, const char *value_name,
    uint32_t type, const void *data, uint32_t data_bytes)
{
    char name[MAX_NAME+1];
    if (!normalise(name,sizeof name,value_name,0) ||
        (type!=FT5955_REG_SZ && type!=FT5955_REG_BINARY &&
         type!=FT5955_REG_DWORD) ||
        data_bytes>MAX_DATA || (data_bytes && !data) ||
        (type==FT5955_REG_DWORD && data_bytes!=4) ||
        (type==FT5955_REG_SZ &&
         (!data_bytes || !data ||
          ((const unsigned char *)data)[data_bytes-1]!=0)))
        return ERROR_INVALID_PARAMETER;
    pthread_mutex_lock(&registry_lock);
    struct location at;
    if(!location_of(hkey,&at)) {
        pthread_mutex_unlock(&registry_lock); return ERROR_INVALID_HANDLE;
    }
    if(!(at.access & FT5955_KEY_SET_VALUE)) {
        pthread_mutex_unlock(&registry_lock); return ERROR_ACCESS_DENIED;
    }
    char path[MAX_PATH+1];
    if(!key_path(path,at.path,subkey)) {
        pthread_mutex_unlock(&registry_lock); return ERROR_INVALID_PARAMETER;
    }
    int key=lookup_key(at.root,path);
    /* Check value capacity before creating intermediate keys. */
    int existing=key<0 ? -1 : lookup_value((unsigned)key,name);
    if(existing<0 && nvalues==MAX_VALUES) {
        pthread_mutex_unlock(&registry_lock); return ERROR_NOT_ENOUGH_MEMORY;
    }
    if(key<0) key=create_path(at.root,path);
    if(key<0) {
        pthread_mutex_unlock(&registry_lock); return ERROR_NOT_ENOUGH_MEMORY;
    }
    int index=lookup_value((unsigned)key,name);
    if (index<0) {
        index=(int)nvalues++;
        values[index].key_index=(unsigned)key;
        strcpy(values[index].name,name);
    }
    struct value_item *value=&values[index];
    value->type=type; value->length=data_bytes;
    if(data_bytes) memcpy(value->bytes,data,data_bytes);
    pthread_mutex_unlock(&registry_lock); return ERROR_SUCCESS;
}
