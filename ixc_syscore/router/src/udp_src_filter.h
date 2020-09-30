/** 捕获指定机器的UDP和UDPLite流量 **/
#ifndef IXC_UDP_SRC_FILTER_H
#define IXC_UDP_SRC_FILTER_H

#include "mbuf.h"

struct ixc_udp_src_filter{
    unsigned char ip6_subnet[16];
    unsigned char ip6_mask[16];

    unsigned char ip_subnet[4];
    unsigned char ip_mask[4];

    // 是否已经打开了P2P
    int is_opened;
    // 是否是链路层数据
    int is_linked;
};

int ixc_udp_src_filter_init(void);
void ixc_udp_src_filter_uninit(void);

int ixc_udp_src_filter_enable(int enable,int is_linked);
int ixc_udp_src_filter_set(unsigned char *subnet,unsigned char prefix,int is_ipv6);

void ixc_udp_src_filter_handle(struct ixc_mbuf *m);


#endif