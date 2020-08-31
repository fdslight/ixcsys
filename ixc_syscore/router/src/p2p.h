/** 捕获指定机器的UDP和UDPLite流量 **/
#ifndef IXC_P2P_H
#define IXC_P2P_H

#include "mbuf.h"

struct ixc_p2p{
    unsigned char ip6_subnet[16];
    unsigned char ip6_mask[16];

    unsigned char ip_subnet[4];
    unsigned char ip_mask[4];

    // 是否已经打开了P2P
    int is_opened;
};

int ixc_p2p_init(void);
void ixc_p2p_uninit(void);

int ixc_p2p_enable(int enable);
int ixc_p2p_set(unsigned char *subnet,unsigned char prefix,int is_ipv6);

void ixc_p2p_handle(struct ixc_mbuf *m);


#endif