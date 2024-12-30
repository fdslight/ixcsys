#ifndef IXC_NETIF_H
#define IXC_NETIF_H

#include "mbuf.h"

#include "../../pywind/clib/ev/ev.h"

#define IXC_NETIF_READ_NUM 64

struct ixc_netif{
    struct ixc_mbuf *sent_first;
    struct ixc_mbuf *sent_last;

    char devname[512];
    int is_used;
    int fd;
    // 写入标志
    int write_flags;
    char pad[4];
};

int ixc_netif_init(struct ev_set *ev_set);
void ixc_netif_uninit(void);

int ixc_netif_create(const char *devname);
void ixc_netif_delete(void);
int ixc_netif_send(struct ixc_mbuf *m);

/// 发送数据
int ixc_netif_tx_data(struct ixc_netif *netif);
/// 接收数据
int ixc_netif_rx_data(struct ixc_netif *netif);
/// 获取网卡索引值
struct ixc_netif *ixc_netif_get(void);

#endif