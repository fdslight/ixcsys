#ifndef IXC_IP_H
#define IXC_IP_H

#include "mbuf.h"

#define IXC_IPADDR_UNSPEC {0x00,0x00,0x00,0x00}

void ixc_ip_handle(struct ixc_mbuf *mbuf);
int ixc_ip_send(struct ixc_mbuf *m);

#endif