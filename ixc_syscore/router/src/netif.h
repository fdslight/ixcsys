#ifndef IXC_NETIF_H
#define IXC_NETIF_H

#include "mbuf.h"

#include "../../../pywind/clib/ev/ev.h"

#define IXC_NETIF_READ_NUM 32
#define IXC_NETIF_MAX 2

#define IXC_NETIF_LAN 0
#define IXC_NETIF_WAN 1

struct ixc_netif{
    struct ixc_mbuf *sent_first;
    struct ixc_mbuf *sent_last;
    char devname[512];
    int is_used;
    int type;
    int fd;
    // 写入标志
    int write_flags;
    // 是否设置了IPv4
    int isset_ip;
    // 是否设置了IPv6
    int isset_ip6;
    
    // IPv4 MTU大小
    int mtu_v4;
    // IPv6 MTU大小
    int mtu_v6;

    unsigned char ipaddr[4];
    unsigned char ip_mask[4];
    unsigned char ip_subnet[4];
    int ip_prefix;


    unsigned char ip6addr[16];
    unsigned char ip6_mask[16];
    unsigned char ip6_subnet[16];

    // IPv6的本地链路地址
    unsigned char ip6_local_link_addr[16];
    unsigned char ip6_local_link_mask[16];
    unsigned char ip6_local_link_subnet[16];
    int ip6_prefix;

    unsigned char pad1[2];
    //
    unsigned char hwaddr[6];
    unsigned char pad2[2];
    // IPv6的默认路由器
    unsigned char ip6_default_router_hwaddr[6];
};

int ixc_netif_init(struct ev_set *ev_set);
void ixc_netif_uninit(void);

int ixc_netif_create(const char *devname,char res_devname[],int if_idx);
void ixc_netif_delete(int if_idx);
int ixc_netif_set_ip(int if_idx,unsigned char *ipaddr,unsigned char prefix,int is_ipv6);

/// 设置硬件地址
int ixc_netif_set_hwaddr(int if_idx,unsigned char *hwaddr);

int ixc_netif_send(struct ixc_mbuf *m);

/// 发送数据
int ixc_netif_tx_data(struct ixc_netif *netif);
/// 接收数据
int ixc_netif_rx_data(struct ixc_netif *netif);
/// 获取网卡索引值
struct ixc_netif *ixc_netif_get(int if_idx);
/// 获取空的WAN网卡索引
int ixc_netif_no_used_get(void);
/// 检查是否在使用
int ixc_netif_is_used(int if_idx);
/// 检查是否和当前网卡在同一个网段
// 如果指定is_ipv6不为空,那么后面的is_ip6_local_link参数将不会被忽略
int ixc_netif_is_subnet(struct ixc_netif *netif,unsigned char *ip,int is_ipv6,int is_ip6_local_link);
/// 获取同网段的netif
struct ixc_netif *ixc_netif_get_with_subnet_ip(unsigned char *ip,int is_ipv6);

///不要设置IP地址
int ixc_netif_unset_ip(int if_idx,int is_ipv6);

#endif