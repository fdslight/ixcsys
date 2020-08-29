#ifndef IXC_NETIF_H
#define IXC_NETIF_H

#include "mbuf.h"

#define IXC_NETIF_READ_NUM 10

struct ixc_netif{
    struct ixc_mbuf *sent_first;
    struct ixc_mbuf *sent_last;
    // LAN网卡
#define IXC_NETIF_TYPE_LAN 0
    // WAN网卡
#define IXC_NETIF_TYPE_WAN 1
    int type;
    int fd;
    // 写入标志
    int write_flags;

    unsigned char hwaddr[6];
};

int ixc_netif_create(const char *devname,char *res_devname[],int flags);
void ixc_netif_delete(const char *devname,int flags);


int ixc_netif_send(struct ixc_mbuf *m);

/// 发送数据
int ixc_netif_tx_data(struct ixc_netif *netif);
/// 接收数据
int ixc_netif_rx_data(struct ixc_netif *netif);

#endif