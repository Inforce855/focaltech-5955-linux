/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Small, in-memory Windows ANSI registry for the gated 5955 MOH bridge.
 * Does not read/write the Windows registry, Linux files or user settings.
 */
#ifndef FT5955_COMPAT_REGISTRY_H
#define FT5955_COMPAT_REGISTRY_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_REG_MS __attribute__((ms_abi))
#else
#error The MOH engine bridge requires x86-64 GCC/Clang
#endif
#define FT5955_HKEY_CURRENT_USER ((void *)(uintptr_t)0x80000001u)
#define FT5955_HKEY_LOCAL_MACHINE ((void *)(uintptr_t)0x80000002u)
#define FT5955_REG_SZ 1u
#define FT5955_REG_BINARY 3u
#define FT5955_REG_DWORD 4u
#define FT5955_KEY_QUERY_VALUE 0x0001u
#define FT5955_KEY_SET_VALUE 0x0002u
#define FT5955_KEY_READ 0x00020019u
#define FT5955_KEY_WRITE 0x00020006u

uint32_t FT5955_REG_MS ft5955_RegOpenKeyExA(
    void *hkey, const char *subkey, uint32_t options,
    uint32_t access, void **result);
uint32_t FT5955_REG_MS ft5955_RegQueryValueExA(
    void *hkey, const char *value_name, uint32_t *reserved,
    uint32_t *type, unsigned char *data, uint32_t *data_bytes);
uint32_t FT5955_REG_MS ft5955_RegCloseKey(void *hkey);
uint32_t FT5955_REG_MS ft5955_RegSetKeyValueA(
    void *hkey, const char *subkey, const char *value_name,
    uint32_t type, const void *data, uint32_t data_bytes);
#endif
