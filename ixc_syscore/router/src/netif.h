#ifndef IXC_NETIF_H
#define IXC_NETIF_H

#include "mbuf.h"

#define IXC_NETIF_READ_NUM 10
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

    unsigned char ipaddr[4];
    unsigned char mask_v4[4];
    unsigned char ip6addr[16];
    unsigned char mask_v6[16];

    // IPv6的本地链路地址
    unsigned char ip6_local_link_addr[16];
    // IPv6的本地链路前缀
    unsigned char ip6_local_link_prefix;

    unsigned char hwaddr[6];
};

int ixc_netif_init(void);
void ixc_netif_uninit(void);

int ixc_netif_create(const char *devname,char res_devname[],int if_idx);
void ixc_netif_delete(int if_idx);
int ixc_netif_set_ip(int if_idx,unsigned char *ipaddr,unsigned char prefix,int is_ipv6);

/// 刷新硬件地址
int ixc_netif_refresh_hwaddr(int if_idx);

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


#endif