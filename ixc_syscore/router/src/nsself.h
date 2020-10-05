/** 处理访问协议栈的IP地址 **/
#ifndef IXC_NSSELF_H
#define IXC_NSSELF_H

#include "mbuf.h"

int ixc_nsself_init(void);
void ixc_nsself_uninit(void);

void ixc_nsself_handle(struct ixc_mbuf *m);

#endif