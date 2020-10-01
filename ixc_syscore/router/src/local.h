#ifndef IXC_LOCAL_H
#define IXC_LOCAL_H

#include "mbuf.h"

#define IXC_LOCAL_READ_NUM 10

int ixc_local_init(void);
void ixc_local_uninit(void);

/// 创建tun设备
int ixc_local_dev_create(char *name);
/// 删除tun设备
void ixc_local_dev_delete(void);

int ixc_local_rx_data(void);
int ixc_local_tx_data(void);

int ixc_local_set_ip(unsigned char *ipaddr,int is_ipv6,int is_ipv6_local_linked);
void ixc_local_send(struct ixc_mbuf *m);

#endif