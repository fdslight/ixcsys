#ifndef IXC_NATv6_H
#define IXC_NATv6_H

#include "mbuf.h"

int ixc_natv6_init(void);
void ixc_natv6_uninit(void);

void ixc_natv6_handle(struct ixc_mbuf *m);


#endif