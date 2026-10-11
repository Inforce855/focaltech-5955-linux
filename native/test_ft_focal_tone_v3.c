#include "ft_focal_tone_v3.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_invalid_args(void) {
    int16_t x[5120]={0}; uint8_t o[5120]; struct ft5955_tone_v3_metrics m;
    memset(o,123,sizeof o);
    assert(ft5955_tone_v3_normalize(NULL,5120,o,5120,&m)==-1);
    assert(ft5955_tone_v3_normalize(x,5119,o,5120,&m)==-1);
    assert(ft5955_tone_v3_normalize(x,5120,o,5119,&m)==-1);
    assert(ft5955_tone_v3_normalize(x,5120,NULL,5120,&m)==-1);
    assert(ft5955_tone_v3_normalize(x,5120,o,5120,NULL)==-1);
    assert(o[0]==123);
}
static void test_flat(void) {
    int16_t x[5120]; uint8_t o[5120]; struct ft5955_tone_v3_metrics m;
    for(size_t i=0;i<5120;i++)x[i]=600;
    assert(ft5955_tone_v3_normalize(x,5120,o,5120,&m)==1);
    assert(m.input_min==600 && m.input_max==600);
    for(size_t i=0;i<5120;i++)assert(o[i]==0);
}
static void test_negative_rejected_without_output_mutation(void) {
    int16_t x[5120]={0}; uint8_t o[5120]; struct ft5955_tone_v3_metrics m;
    x[2]=-1;
    memset(o,231,sizeof o);
    assert(ft5955_tone_v3_normalize(x,5120,o,5120,&m)==-2);
    assert(o[0]==231 && o[5119]==231);
}
static void test_elf_epsilon_changes_max_intensity(void) {
    int16_t x[5120]; uint8_t o[5120]; struct ft5955_tone_v3_metrics m;
    for(size_t i=0;i<5120;i++)x[i]=(int16_t)(i%1024);
    assert(ft5955_tone_v3_normalize(x,5120,o,5120,&m)==0);
    assert(m.cutoff.cutoff_bin==250);
    assert(m.scaling_denominator_integer==1023);
    /* Vendor ELF's +1e-6 denominator makes 255 become 254.999999...,
     * truncated to 254. Earlier v2 incorrectly produced 255. */
    assert(o[0]==254 && o[1023]==0);
    assert(o[10]>=o[100] && o[100]>=o[1000]);
}
static void test_nondefault_cutoff_works(void) {
    int16_t x[5120]; uint8_t o[5120]; struct ft5955_tone_v3_metrics m;
    for(size_t i=0;i<5120;i++)x[i]=600;
    x[0]=0;x[1]=1000;
    assert(ft5955_tone_v3_normalize(x,5120,o,5120,&m)==0);
    assert(m.cutoff.cutoff_bin==141);
    assert(m.scaling_denominator_integer==564);
    assert(o[0]==255 && o[1]==0 && o[30]==180);
}
static void test_immutable_and_deterministic(void) {
    int16_t x[5120],copy[5120]; uint8_t a[5120],b[5120];
    struct ft5955_tone_v3_metrics ma,mb;
    for(size_t i=0;i<5120;i++)x[i]=(int16_t)(1000+(i*37u)%1700u);
    memcpy(copy,x,sizeof x);
    assert(ft5955_tone_v3_normalize(x,5120,a,5120,&ma)==0);
    assert(ft5955_tone_v3_normalize(x,5120,b,5120,&mb)==0);
    assert(memcmp(copy,x,sizeof x)==0);
    assert(memcmp(a,b,sizeof a)==0 && memcmp(&ma,&mb,sizeof ma)==0);
}
int main(void) {
    test_invalid_args();test_flat();test_negative_rejected_without_output_mutation();
    test_elf_epsilon_changes_max_intensity();test_nondefault_cutoff_works();
    test_immutable_and_deterministic();
    puts("PASS: 6 synthetic-only ELF-arithmetic tone-map regression tests");
    puts("Offline mathematical checks only; vendor library NOT executed.");
    return 0;
}
