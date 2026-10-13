/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Synthetic PE export-directory regression tests, no DLL execution.
 */
#include "ft5955_pe_exports.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define IMAGE_SIZE 0x2000u
#define DIRECTORY  0x200u
#define DIR_SIZE   0x40u
#define FUNCTIONS  0x300u
#define NAMES      0x320u
#define ORDINALS   0x340u
#define NAME       0x400u
#define CODE_RVA   0x1000u
static unsigned failures;
#define CHECK(e) do { if(!(e)) { \
    fprintf(stderr,"export test line %d: %s\n",__LINE__,#e); \
    failures++; } } while(0)
static void wr16(uint8_t *b,size_t n,uint16_t x){ memcpy(b+n,&x,2); }
static void wr32(uint8_t *b,size_t n,uint32_t x){ memcpy(b+n,&x,4); }
static void fixture(uint8_t *b)
{
    memset(b,0,IMAGE_SIZE);
    wr32(b,DIRECTORY+20,1); /* NumberOfFunctions */
    wr32(b,DIRECTORY+24,1); /* NumberOfNames */
    wr32(b,DIRECTORY+28,FUNCTIONS);
    wr32(b,DIRECTORY+32,NAMES);
    wr32(b,DIRECTORY+36,ORDINALS);
    wr32(b,FUNCTIONS,CODE_RVA);
    wr32(b,NAMES,NAME);
    wr16(b,ORDINALS,0);
    memcpy(b+NAME,"WbioQueryEngineInterface",25);
}
static void reject(uint8_t *b,uint32_t dir,uint32_t size,const char *name)
{
    uint32_t out=0xa5a5a5a5u;
    int result=ft5955_pe_find_export(b,IMAGE_SIZE,dir,size,name,&out);
    CHECK(result == -1);
    CHECK(out == 0xa5a5a5a5u);
}
int main(void)
{
    uint8_t b[IMAGE_SIZE];
    uint32_t out=0;
    fixture(b);
    CHECK(ft5955_pe_find_export(b,IMAGE_SIZE,DIRECTORY,DIR_SIZE,
         "WbioQueryEngineInterface",&out)==0);
    CHECK(out == CODE_RVA);
    reject(b,DIRECTORY,DIR_SIZE,"WrongExport");
    reject(b,0,DIR_SIZE,"WbioQueryEngineInterface");
    reject(b,IMAGE_SIZE-8,DIR_SIZE,"WbioQueryEngineInterface");
    reject(b,DIRECTORY,20,"WbioQueryEngineInterface");
    fixture(b); wr32(b,DIRECTORY+20,0); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,DIRECTORY+24,2); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,DIRECTORY+28,IMAGE_SIZE-2); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,DIRECTORY+32,IMAGE_SIZE-2); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,DIRECTORY+36,IMAGE_SIZE-1); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,NAMES,IMAGE_SIZE); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,NAMES,IMAGE_SIZE-4); memset(b+IMAGE_SIZE-4,'Q',4);
    reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface"); /* unterminated */
    fixture(b); wr16(b,ORDINALS,1); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,FUNCTIONS,0); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,FUNCTIONS,IMAGE_SIZE); reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface");
    fixture(b); wr32(b,FUNCTIONS,DIRECTORY+0x24);
    reject(b,DIRECTORY,DIR_SIZE,"WbioQueryEngineInterface"); /* forwarder */
    fixture(b); reject(b,DIRECTORY,DIR_SIZE,"");
    fixture(b);
    CHECK(ft5955_pe_find_export(NULL,IMAGE_SIZE,DIRECTORY,DIR_SIZE,
        "WbioQueryEngineInterface",&out)==-1);
    CHECK(ft5955_pe_find_export(b,IMAGE_SIZE,DIRECTORY,DIR_SIZE,
        "WbioQueryEngineInterface",NULL)==-1);
    if (failures) {
        fprintf(stderr,"5955 PE export parser: %u test failures\n",failures);
        return 1;
    }
    puts("5955 bounded PE export lookup: synthetic tests OK");
    return 0;
}
