#ifndef IXC_NETIF_H
#define IXC_NETIF_H

#include "mbuf.h"

#define IXC_NETIF_READ_NUM 10

struct ixc_netif{
    struct ixc_mbuf *sent_first;
    struct ixc_mbuf *sent_last;
    char devname[512];
    int is_used;
    int fd;
    // 写入标志
    int write_flags;

    unsigned char ipaddr[4];
    unsigned char mask_v4[4];
    unsigned char ip6addr[16];
    unsigned char mask_v6[16];

    unsigned char hwaddr[6];
};

int ixc_netif_init(void);
void ixc_netif_uninit(void);

int ixc_netif_create(const char *devname,char res_devname[]);
void ixc_netif_delete(void);
int ixc_netif_set_ip(unsigned char *ipaddr,unsigned char prefix,int is_ipv6);

/// 刷新硬件地址
int ixc_netif_refresh_hwaddr(void);


int ixc_netif_send(struct ixc_mbuf *m);

/// 发送数据
int ixc_netif_tx_data(void);
/// 接收数据
int ixc_netif_rx_data(void);

#endif