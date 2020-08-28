#ifndef IXC_NETIF_H
#define IXC_NETIF_H

#include "mbuf.h"

int ixc_netif_create(const char *devname,char *res_devname[],int flags);
void ixc_netif_delete(const char *devname,int flags);


int ixc_netif_send(struct ixc_mbuf *m);

/// 发送数据
int ixc_netif_tx_data(void);

/// 接收数据
int ixc_netif_rx_data(void);

#endif