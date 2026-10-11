#include "ft_focal_tone_v2.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

static void test_bad(void) {
    int16_t x[5120]={0}; uint8_t out[5120]; struct ft5955_tone_v2_metrics m;
    memset(out, 0x7b, sizeof out);
    assert(ft5955_focal_tone_v2_research(NULL,5120,out,5120,&m)==-1);
    assert(ft5955_focal_tone_v2_research(x,5119,out,5120,&m)==-1);
    assert(ft5955_focal_tone_v2_research(x,5120,out,5119,&m)==-1);
    assert(ft5955_focal_tone_v2_research(x,5120,NULL,5120,&m)==-1);
    assert(ft5955_focal_tone_v2_research(x,5120,out,5120,NULL)==-1);
    assert(out[0]==0x7b);
}
static void test_flat(void) {
    int16_t x[5120]; uint8_t out[5120]; struct ft5955_tone_v2_metrics m;
    for(size_t i=0;i<5120;i++) x[i]=1150;
    memset(out,1,sizeof out);
    assert(ft5955_focal_tone_v2_research(x,5120,out,5120,&m)==1);
    for(size_t i=0;i<5120;i++)assert(out[i]==0);
    assert(m.inverted_min==-1150 && m.inverted_max==-1150);
}
static void test_ramp_and_cutoff(void) {
    int16_t x[5120]; uint8_t out[5120]; struct ft5955_tone_v2_metrics m;
    for(size_t i=0;i<5120;i++) x[i]=(int16_t)(i%1024);
    assert(ft5955_focal_tone_v2_research(x,5120,out,5120,&m)==0);
    assert(out[0]==255 && out[1023]==0);
    assert(out[10]>=out[100] && out[100]>=out[1000]);
    assert(m.dynamic_range==1023);
    assert(m.effective_range==1023*m.cutoff.cutoff_bin/250);
    /* Synthetic concentrated image: the histogram cutoff should actually
     * move, unlike the fixed cap we originally modelled. */
    for (size_t i=0; i<5120; ++i) x[i] = 600;
    x[0] = 0;
    x[1] = 1000;
    assert(ft5955_focal_tone_v2_research(x,5120,out,5120,&m)==0);
    assert(m.cutoff.high_tail_branch==0);
    assert(m.cutoff.cutoff_bin == 141);
    assert(m.effective_range == 564);
    assert(out[0] == 255 && out[1] == 0);
    assert(out[30] == 180);
}
static void test_high_tail_and_sparse(void) {
    int16_t x[5120]; uint8_t out[5120]; struct ft5955_tone_v2_metrics m;
    for(size_t i=0;i<5120;i++)x[i]=i<4000?140:1000;
    x[3]=0; x[1]=200; x[2]=500;
    assert(ft5955_focal_tone_v2_research(x,5120,out,5120,&m)==0);
    assert(m.cutoff.high_tail_branch==1);
    assert(m.cutoff.cutoff_bin>=50 && m.cutoff.cutoff_bin<=250);
    assert(m.effective_range<=m.dynamic_range);
    assert(out[3]==255 && out[4000]==0);
}
static void test_signed_extremes_and_no_mutation(void) {
    int16_t x[5120], copy[5120]; uint8_t a[5120],b[5120];
    struct ft5955_tone_v2_metrics ma,mb;
    for(size_t i=0;i<5120;i++)x[i]=(int16_t)((i*37u)%32760u);
    x[0]=INT16_MIN; x[1]=INT16_MAX;
    memcpy(copy,x,sizeof x);
    assert(ft5955_focal_tone_v2_research(x,5120,a,5120,&ma)==0);
    assert(ft5955_focal_tone_v2_research(x,5120,b,5120,&mb)==0);
    assert(memcmp(x,copy,sizeof x)==0);
    assert(memcmp(a,b,sizeof a)==0);
    assert(memcmp(&ma,&mb,sizeof ma)==0);
    assert(ma.dynamic_range==65535);
}
int main(void){
    test_bad();test_flat();test_ramp_and_cutoff();test_high_tail_and_sparse();test_signed_extremes_and_no_mutation();
    puts("PASS: 5 synthetic-only FocalTech cutoff-integrated tone-map tests");
    puts("Offline approximation; no USB, biometric images, proprietary binaries or authentication.");
}
