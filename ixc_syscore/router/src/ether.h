#ifndef IXC_ETHER_H
#define IXC_ETHER_H

#include "mbuf.h"

#pragma pack(push)
#pragma pack(1)

struct ixc_ether_header{
    unsigned char dst_hwaddr[6];
    unsigned char src_hwaddr[6];
    union{
        unsigned short type;
        unsigned short length;
    };
};

#pragma pack(pop)

/// 发送二层数据包
// add_header 如果不为0表示需要系统填充以太网头部
int ixc_ether_send(struct ixc_mbuf *mbuf,int add_header);
void ixc_ether_handle(struct ixc_mbuf *mbuf);

int ixc_ether_send2(struct ixc_mbuf *m);

/// 通过IP地址获取多播硬件地址
int ixc_ether_get_multi_hwaddr_by_ip(unsigned char *ip,unsigned char *result);
/// 通过IPv6地址获取多播地址
int ixc_ether_get_multi_hwaddr_by_ipv6(unsigned char *ip6,unsigned char *result);

#endif