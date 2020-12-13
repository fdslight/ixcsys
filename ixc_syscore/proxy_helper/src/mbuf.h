#ifndef IP2SOCKS_MBUF_H
#define IP2SOCKS_MBUF_H

#include<sys/types.h>

struct mbuf_pool{
    struct mbuf *empty_head;
    // 预先分配大小
    unsigned int pre_alloc_num;
    // 当前分配大小
    unsigned int cur_alloc_num;
};

struct mbuf{
    struct mbuf *next;
    void *priv_data;
    int priv_flags;
#define MBUF_BEGIN 256
    int begin;
    int offset;
    int tail;
    int end; 
#define IXC_MBUF_DATA_MAX_SIZE 0x101ff
    unsigned char data[IXC_MBUF_DATA_MAX_SIZE];
};

int mbuf_init(size_t pre_alloc_size);
void mbuf_uninit(void);

struct mbuf *mbuf_get(void);
void mbuf_put(struct mbuf *m);

#endif