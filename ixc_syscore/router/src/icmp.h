#ifndef IXC_ICMP_H
#define IXC_ICMP_H

#include "mbuf.h"

void ixc_icmp_handle(struct ixc_mbuf *m,int is_self);

#endif