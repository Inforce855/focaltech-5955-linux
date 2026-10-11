CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror

.PHONY: all test clean
all: build/test_ft_image

build:
	mkdir -p build

build/test_ft_image: ft_image.c ft_image.h test_ft_image.c | build
	$(CC) $(CFLAGS) -o $@ ft_image.c test_ft_image.c

test: build/test_ft_image
	./build/test_ft_image

clean:
	rm -rf build
