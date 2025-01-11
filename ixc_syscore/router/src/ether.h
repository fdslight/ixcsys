#ifndef IXC_ETHER_H
#define IXC_ETHER_H

#include "mbuf.h"
#include "netif.h"

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

struct ixc_ether_vlan_header{
    unsigned char dst_hwaddr[6];
    unsigned char src_hwaddr[6];
    unsigned short tpid;
    unsigned short vlan_info;
    unsigned short type;
};

#pragma pack(pop)

/// 发送二层数据包
// add_header 如果不为0表示需要系统填充以太网头部
int ixc_ether_send(struct ixc_mbuf *mbuf,int add_header);
void ixc_ether_handle(struct ixc_mbuf *mbuf);

int ixc_ether_send2(struct ixc_mbuf *m);

/// 发送VLAN格式数据包
int ixc_ether_send3(struct ixc_mbuf *m,unsigned short tpid,unsigned short vlan_id);

/// 通过IP地址获取多播硬件地址
int ixc_ether_get_multi_hwaddr_by_ip(unsigned char *ip,unsigned char *result);
/// 通过IPv6地址获取多播地址
int ixc_ether_get_multi_hwaddr_by_ipv6(unsigned char *ip6,unsigned char *result);
/// 是否是自身的地址
int ixc_ether_is_self(struct ixc_netif *netif,unsigned char *hwaddr);

int ixc_ether_net_monitor_set(int enable,unsigned char *hwaddr);

#endif
