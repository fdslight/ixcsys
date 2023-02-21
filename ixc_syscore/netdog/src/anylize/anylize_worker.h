#ifndef IXC_ANYLIZE_WORKER_H
#define IXC_ANYLIZE_WORKER_H

#include "../mbuf.h"

int ixc_anylize_worker_init(void);
void ixc_anylize_worker_uninit(void);
void ixc_anylize_netpkt(struct ixc_mbuf *m);

#endif