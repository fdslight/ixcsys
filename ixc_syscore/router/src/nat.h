#ifndef IXC_NAT_H
#define IXC_NAT_H

#include "mbuf.h"

int ixc_nat_init(void);
void ixc_nat_uninit(void);

void ixc_nat_handle(struct ixc_mbuf *m);

#endif