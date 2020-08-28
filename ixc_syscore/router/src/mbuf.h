#ifndef IXC_MBUF_H
#define IXC_MBUF_H

#include<sys/types.h>

#include "netif.h"

struct ixc_mbuf{
    struct ixc_netif *netif;
    struct ixc_mbuf *next;
    // 开始位置
#define IXC_MBUF_BEGIN 256
    int begin;
    // 偏移位置
    int offset;
    // 尾部
    int tail;
    // 结束位置
    int end;
    unsigned char data[0xffff];
};


int ixc_mbuf_init(size_t pre_alloc_num);
void ixc_mbuf_uninit(void);

struct ixc_mbuf *ixc_mbuf_get(void);
void ixc_mbuf_put(struct ixc_mbuf *m);

#endif