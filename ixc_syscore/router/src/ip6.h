#ifndef IXC_IP6_H
#define IXC_IP6_H

#include "mbuf.h"

void ixc_ip6_handle(struct ixc_mbuf *mbuf);

int ixc_ip6_send(struct ixc_mbuf *mbuf);

#endif