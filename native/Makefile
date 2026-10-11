CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror

.PHONY: all test clean
all: build/test_ft_image build/test_ft_histogram build/test_ft_focal_histogram build/test_ft_focal_tone build/test_ft_focal_cutoff build/test_ft_focal_tone_v2

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

test: build/test_ft_image build/test_ft_histogram build/test_ft_focal_histogram build/test_ft_focal_tone build/test_ft_focal_cutoff build/test_ft_focal_tone_v2
	./build/test_ft_image
	./build/test_ft_histogram
	./build/test_ft_focal_histogram
	./build/test_ft_focal_tone
	./build/test_ft_focal_cutoff
	./build/test_ft_focal_tone_v2

clean:
	rm -rf build
