/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Restricted, fail-closed Win32 locale compatibility for the MOH matcher.
 * Currently supports en-GB, en-US and invariant locale identifiers only.
 */
#ifndef FT5955_COMPAT_LOCALE_H
#define FT5955_COMPAT_LOCALE_H
#include <stdint.h>
#if defined(__x86_64__) && defined(__GNUC__)
#define FT5955_LOCALE_MS __attribute__((ms_abi))
#else
#error FT5955 compatibility layer requires x86-64 GCC or Clang
#endif
#define FT5955_LCID_EN_US 0x0409u
#define FT5955_LCID_EN_GB 0x0809u
#define FT5955_LCID_INVARIANT 0x007fu
#define FT5955_LCID_USER_DEFAULT 0x0400u
#define FT5955_LCID_SYSTEM_DEFAULT 0x0800u
#define FT5955_LCID_INSTALLED 0x00000001u
#define FT5955_LCID_SUPPORTED 0x00000002u
uint32_t FT5955_LOCALE_MS ft5955_GetUserDefaultLCID(void);
int FT5955_LOCALE_MS ft5955_IsValidLocale(uint32_t lcid, uint32_t flags);
/* Narrow Win32 LCTYPE support; unknown types and flags return failure. */
#define FT5955_LTYPE_SLIST 0x000cu
#define FT5955_LTYPE_SDECIMAL 0x000eu
#define FT5955_LTYPE_STHOUSAND 0x000fu
#define FT5955_LTYPE_SDATE 0x001du
#define FT5955_LTYPE_STIME 0x001eu
#define FT5955_LTYPE_SSHORTDATE 0x001fu
#define FT5955_LTYPE_SLONGDATE 0x0020u
#define FT5955_LTYPE_S1159 0x0028u
#define FT5955_LTYPE_S2359 0x0029u
#define FT5955_LTYPE_SNAME 0x005cu
#define FT5955_LTYPE_STIMEFORMAT 0x1003u
int FT5955_LOCALE_MS ft5955_GetLocaleInfoW(
    uint32_t lcid, uint32_t type, uint16_t *output, int capacity);
#endif
