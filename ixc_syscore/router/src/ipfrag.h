#ifndef IXC_IPFRAG_H
#define IXC_IPFRAG_H

#include "mbuf.h"

int ixc_ipfrag_init(void);
void ixc_ipfrag_uninit(void);

/// 对IP数据包进行分片
struct ixc_mbuf *ixc_ipfrag_frag(struct ixc_mbuf *m);

#endif