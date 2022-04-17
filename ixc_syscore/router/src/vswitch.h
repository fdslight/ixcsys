/** 虚拟交换接口 **/
#ifndef IXC_VSWITCH_H
#define IXC_VSWITCH_H

#include "mbuf.h"

struct ixc_vsw{
    unsigned char ip6_subnet[16];
    unsigned char ip6_mask[16];
    unsigned char ip4_subnet[4];
    unsigned char ip4_mask[4];

    // 是否开启IPv4虚拟交换
    int ip4_enable;
    // 是否开启IPv6虚拟交换
    int ip6_enable;

    unsigned char ip6_prefix;
    unsigned char ip4_prefix;
};

int ixc_vsw_init(void);
void ixc_vsw_uninit(void);

///  打开或者关闭虚拟交换
int ixc_vsw_enable(int enable,int is_ipv6);

/// 设置子网
int ixc_vsw_set_subnet(unsigned char *subnet,unsigned char prefix,int is_ipv6);

/// 是否来自于虚拟交换的子网
int ixc_vsw_is_from_subnet(unsigned char *address,int is_ipv6);

/// 处理来自于user的数据包
void ixc_vsw_handle_from_user(struct ixc_mbuf *mbuf);

#endif