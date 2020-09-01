#ifndef IXC_PPPOE_H
#define IXC_PPPOE_H

#include "mbuf.h"

void ixc_pppoe_send(struct ixc_mbuf *m);
/// 检查PPPOE是否启用
int ixc_pppoe_enable(void);

#endif