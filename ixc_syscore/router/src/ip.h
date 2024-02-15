#ifndef IXC_IP_H
#define IXC_IP_H

#include "mbuf.h"

#define IXC_IPADDR_UNSPEC {0x00,0x00,0x00,0x00}
#define IXC_IPADDR_BROADCAST {0xff,0xff,0xff,0xff}

int ixc_ip_init(void);

void ixc_ip_handle(struct ixc_mbuf *mbuf);
int ixc_ip_send(struct ixc_mbuf *m);
// 开启或者关闭非系统DNS
int ixc_ip_no_system_dns_drop_enable(int enable);

void ixc_ip_uninit(void);



#endif