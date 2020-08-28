#ifndef IXC_ROUTER_H
#define IXC_ROUTER_H

#include<sys/types.h>

/// 表示链路层数据包
#define IXC_PKT_FLAGS_LINK 0
/// 表示IP层数据包
#define IXC_PKT_FLAGS_IP 1

/// 发送数据到Python
int ixc_router_send(void *buf,size_t size,int flags);

#endif