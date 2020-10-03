#ifndef IXC_NATv6_H
#define IXC_NATv6_H

/// 直通模式,不做任何操作
#define IXC_NATv6_TYPE_PASS 0

struct ixc_natv6{
    // 是否开启natv6
    int enable;
    // nat类型
    int type;
};

#include "mbuf.h"

int ixc_natv6_init(void);
void ixc_natv6_uninit(void);

void ixc_natv6_handle(struct ixc_mbuf *m);
int ixc_natv6_enable(int status,int type);

#endif