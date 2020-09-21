#ifndef IXC_ROUTER_H
#define IXC_ROUTER_H

/// 表示是一个DHCP CLIENT数据包
#define IXC_FLAG_DHCP_CLIENT 1
/// 表示是一个DHCP SERVER数据包
#define IXC_FLAG_DHCP_SERVER 2

#include<sys/types.h>

/// 发送数据到Python
// link_proto 表明链路层协议号,如果此参数为0表示IP层数据包
// ipproto表示IP协议号,如果是链路层协议此参数为0
// flags 表示额外的参数补充
int ixc_router_send(unsigned short link_proto,unsigned char ipproto,unsigned char flags,void *buf,size_t size);

/// 写入事件告知
int ixc_router_write_ev_tell(int fd,int flags);

#endif