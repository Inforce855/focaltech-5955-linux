#ifndef MOCK_ENGINE_H
#define MOCK_ENGINE_H
#include <stddef.h>
#include <stdint.h>
int ft_engine_open(const char *path);
uint32_t ft_engine_accept(const uint8_t *img, int w, int h, uint8_t purpose);
int ft_engine_enroll_begin(void);
int ft_engine_enroll_update(void);
int ft_engine_enroll_commit(uint8_t **out,size_t *len);
int ft_engine_verify(const uint8_t *tmpl,size_t len);
#endif
