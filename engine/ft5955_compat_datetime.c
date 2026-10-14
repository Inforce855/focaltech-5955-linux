/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Safe subset of Win32 GetDateFormatW / GetTimeFormatW for the 5955 engine.
 * Explicit patterns and unsupported flags fail closed, not guessed.
 * ASCII English built-in formats only; does not implement Windows NLS.
 */
#define _POSIX_C_SOURCE 200809L
#include "ft5955_compat_datetime.h"
#include "ft5955_compat_locale.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

#define DATE_SHORTDATE 0x00000001u
#define DATE_LONGDATE 0x00000002u
#define DATE_YEARMONTH 0x00000008u
#define TIME_NOMINUTESORSECONDS 0x00000001u
#define TIME_NOSECONDS 0x00000002u
#define TIME_NOTIMEMARKER 0x00000004u
#define TIME_FORCE24HOURFORMAT 0x00000008u

static const char *months[] = {"January","February","March","April","May","June",
                               "July","August","September","October","November","December"};
static const char *weekdays[] = {"Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"};

static int is_leap(int y) { return (y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)); }
static int days_in_month(int y, int m)
{
    const int days[] = {0,31,28,31,30,31,30,31,31,30,31,30,31};
    return days[m] + (m == 2 && is_leap(y));
}
static int valid_date(const ft5955_systemtime *s)
{
    return s->year >= 1601 && s->year <= 9999 && s->month >= 1 &&
           s->month <= 12 && s->day >= 1 &&
           s->day <= days_in_month(s->year, s->month);
}
static int valid_time(const ft5955_systemtime *s)
{
    return s->hour < 24 && s->minute < 60 && s->second < 60 &&
           s->milliseconds < 1000;
}
static int weekday(int y, int m, int d)
{
    static const int t[] = {0,3,2,5,0,3,5,1,4,6,2,4};
    if (m < 3) y--;
    return (y + y / 4 - y / 100 + y / 400 + t[m - 1] + d) % 7;
}
static int get_date_now(ft5955_systemtime *s)
{
    struct timespec current;
    struct tm local;
    if (clock_gettime(CLOCK_REALTIME, &current) || !localtime_r(&current.tv_sec, &local))
        return 0;
    s->year = (uint16_t)(local.tm_year + 1900);
    s->month = (uint16_t)(local.tm_mon + 1);
    s->day = (uint16_t)local.tm_mday;
    s->day_of_week = (uint16_t)local.tm_wday;
    s->hour = (uint16_t)local.tm_hour;
    s->minute = (uint16_t)local.tm_min;
    s->second = (uint16_t)local.tm_sec;
    s->milliseconds = (uint16_t)(current.tv_nsec / 1000000L);
    return 1;
}
static uint32_t resolve_locale(uint32_t lcid)
{
    if (lcid == 0 || lcid == FT5955_LCID_USER_DEFAULT ||
        lcid == FT5955_LCID_SYSTEM_DEFAULT)
        lcid = ft5955_GetUserDefaultLCID();
    return lcid == FT5955_LCID_EN_GB || lcid == FT5955_LCID_EN_US ||
           lcid == FT5955_LCID_INVARIANT ? lcid : 0;
}
static int utf16_result(const char *ascii, uint16_t *output, int capacity)
{
    size_t count = strlen(ascii) + 1;
    if (count > 160 || count > 2147483647u || capacity < 0)
        return 0;
    if (!output && capacity == 0)
        return (int)count;
    if (!output || (size_t)capacity < count)
        return 0;
    for (size_t i = 0; i < count; ++i)
        output[i] = (uint8_t)ascii[i];
    return (int)count;
}

int FT5955_MS_ABI ft5955_GetDateFormatW(uint32_t lcid, uint32_t flags,
    const ft5955_systemtime *date, const uint16_t *format,
    uint16_t *out, int capacity)
{
    const uint32_t locale = resolve_locale(lcid);
    ft5955_systemtime now;
    char result[160];
    if (!locale || format || !(flags == 0 || flags == DATE_SHORTDATE ||
                               flags == DATE_LONGDATE || flags == DATE_YEARMONTH))
        return 0;
    if (!date) {
        if (!get_date_now(&now)) return 0;
        date = &now;
    }
    if (!valid_date(date)) return 0;
    if (flags == DATE_YEARMONTH)
        snprintf(result, sizeof result, "%s %04u", months[date->month - 1], date->year);
    else if (flags == DATE_LONGDATE) {
        const char *dow = weekdays[weekday(date->year, date->month, date->day)];
        if (locale == FT5955_LCID_EN_US)
            snprintf(result, sizeof result, "%s, %s %u, %04u", dow,
                     months[date->month - 1], date->day, date->year);
        else
            snprintf(result, sizeof result, "%s, %u %s %04u", dow,
                     date->day, months[date->month - 1], date->year);
    } else if (locale == FT5955_LCID_EN_GB)
        snprintf(result, sizeof result, "%02u/%02u/%04u", date->day, date->month, date->year);
    else if (locale == FT5955_LCID_EN_US)
        snprintf(result, sizeof result, "%u/%u/%04u", date->month, date->day, date->year);
    else
        snprintf(result, sizeof result, "%04u-%02u-%02u", date->year, date->month, date->day);
    return utf16_result(result, out, capacity);
}

int FT5955_MS_ABI ft5955_GetTimeFormatW(uint32_t lcid, uint32_t flags,
    const ft5955_systemtime *time, const uint16_t *format,
    uint16_t *out, int capacity)
{
    const uint32_t locale = resolve_locale(lcid);
    ft5955_systemtime now;
    char result[160];
    if (!locale || format || (flags & ~15u) ||
        ((flags & TIME_NOMINUTESORSECONDS) && (flags & TIME_NOSECONDS)))
        return 0;
    if (!time) {
        if (!get_date_now(&now)) return 0;
        time = &now;
    }
    if (!valid_time(time)) return 0;
    int is24 = (flags & TIME_FORCE24HOURFORMAT) || locale != FT5955_LCID_EN_US;
    int hour = time->hour;
    if (!is24) hour = hour % 12 ? hour % 12 : 12;
    int n = snprintf(result, sizeof result, is24 ? "%02d" : "%d", hour);
    if (n < 0 || (size_t)n >= sizeof result) return 0;
    if (!(flags & TIME_NOMINUTESORSECONDS)) {
        int written = snprintf(result + n, sizeof result - (size_t)n, ":%02u", time->minute);
        if (written < 0 || (size_t)written >= sizeof result - (size_t)n) return 0;
        n += written;
        if (!(flags & TIME_NOSECONDS)) {
            written = snprintf(result + n, sizeof result - (size_t)n, ":%02u", time->second);
            if (written < 0 || (size_t)written >= sizeof result - (size_t)n) return 0;
            n += written;
        }
    }
    if (!is24 && !(flags & TIME_NOTIMEMARKER)) {
        if ((size_t)n + 4 > sizeof result) return 0;
        strcpy(result + n, time->hour < 12 ? " AM" : " PM");
    }
    return utf16_result(result, out, capacity);
}
