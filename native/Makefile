CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror

.PHONY: all test clean
all: build/test_ft_image build/test_ft_histogram build/test_ft_focal_histogram build/test_ft_focal_tone build/test_ft_focal_cutoff build/test_ft_focal_tone_v2 build/test_ft_focal_tone_v3 build/test_ft_vendor_golden build/test_ft_descriptor_pack build/test_ft_mfs_histogram

build:
	mkdir -p build

build/test_ft_image: ft_image.c ft_image.h test_ft_image.c | build
	$(CC) $(CFLAGS) -o $@ ft_image.c test_ft_image.c

build/test_ft_histogram: ft_histogram.c ft_histogram.h test_ft_histogram.c | build
	$(CC) $(CFLAGS) -o $@ ft_histogram.c test_ft_histogram.c -lm


build/test_ft_focal_histogram: ft_focal_histogram.c ft_focal_histogram.h ft_histogram.c ft_histogram.h test_ft_focal_histogram.c | build
	$(CC) $(CFLAGS) -o $@ ft_focal_histogram.c ft_histogram.c test_ft_focal_histogram.c -lm

build/test_ft_focal_tone: ft_focal_tone.c ft_focal_tone.h ft_focal_histogram.c ft_focal_histogram.h ft_histogram.c ft_histogram.h test_ft_focal_tone.c | build
	$(CC) $(CFLAGS) -o $@ ft_focal_tone.c ft_focal_histogram.c ft_histogram.c test_ft_focal_tone.c -lm

build/test_ft_focal_cutoff: ft_focal_cutoff.c ft_focal_cutoff.h test_ft_focal_cutoff.c | build
	$(CC) $(CFLAGS) -o $@ ft_focal_cutoff.c test_ft_focal_cutoff.c -lm

build/test_ft_focal_tone_v2: ft_focal_tone_v2.c ft_focal_tone_v2.h ft_focal_cutoff.c ft_focal_cutoff.h ft_focal_histogram.c ft_focal_histogram.h ft_histogram.c ft_histogram.h test_ft_focal_tone_v2.c | build
	$(CC) $(CFLAGS) -o $@ ft_focal_tone_v2.c ft_focal_cutoff.c ft_focal_histogram.c ft_histogram.c test_ft_focal_tone_v2.c -lm

build/test_ft_focal_tone_v3: ft_focal_tone_v3.c ft_focal_tone_v3.h ft_focal_cutoff.c ft_focal_cutoff.h ft_focal_histogram.c ft_focal_histogram.h ft_histogram.c ft_histogram.h test_ft_focal_tone_v3.c | build
	$(CC) $(CFLAGS) -o $@ ft_focal_tone_v3.c ft_focal_cutoff.c ft_focal_histogram.c ft_histogram.c test_ft_focal_tone_v3.c -lm

build/test_ft_vendor_golden: ft_focal_tone_v3.c ft_focal_tone_v3.h ft_focal_cutoff.c ft_focal_cutoff.h ft_focal_histogram.c ft_focal_histogram.h ft_histogram.c ft_histogram.h test_ft_vendor_golden.c | build
	$(CC) $(CFLAGS) -o $@ ft_focal_tone_v3.c ft_focal_cutoff.c ft_focal_histogram.c ft_histogram.c test_ft_vendor_golden.c -lm

build/test_ft_descriptor_pack: ft_descriptor_pack.c ft_descriptor_pack.h test_ft_descriptor_pack.c | build
	$(CC) $(CFLAGS) -o $@ ft_descriptor_pack.c test_ft_descriptor_pack.c -lm

build/test_ft_mfs_histogram: ft_mfs_histogram.c ft_mfs_histogram.h test_ft_mfs_histogram.c | build
	$(CC) $(CFLAGS) -o $@ ft_mfs_histogram.c test_ft_mfs_histogram.c -lm

test: build/test_ft_image build/test_ft_histogram build/test_ft_focal_histogram build/test_ft_focal_tone build/test_ft_focal_cutoff build/test_ft_focal_tone_v2 build/test_ft_focal_tone_v3 build/test_ft_vendor_golden build/test_ft_descriptor_pack build/test_ft_mfs_histogram
	./build/test_ft_image
	./build/test_ft_histogram
	./build/test_ft_focal_histogram
	./build/test_ft_focal_tone
	./build/test_ft_focal_cutoff
	./build/test_ft_focal_tone_v2
	./build/test_ft_focal_tone_v3
	./build/test_ft_vendor_golden
	./build/test_ft_descriptor_pack
	./build/test_ft_mfs_histogram

clean:
	rm -rf build
