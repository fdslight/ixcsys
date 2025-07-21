/* 实现前缀转换的ipv6 NAT */
#ifndef IXC_NAT66_H
#define IXC_NAT66_H

#include "mbuf.h"

struct ixc_nat66{
    unsigned char lan_ip6subnet[16];
    unsigned char wan_ip6subnet[16];

    unsigned char wan_prefix;

    int enable;
};

int ixc_nat66_init(void);
void ixc_nat66_uninit(void);

int ixc_nat66_enable(int enable);
int ixc_nat66_is_enabled(void);

int ixc_nat66_set_wan_prefix(unsigned char *lan_prefix,unsigned char *wan_prefix,unsigned char prefix_length);
// 修改前缀
void ixc_nat66_prefix_modify(struct ixc_mbuf *m,int is_src);

#endif