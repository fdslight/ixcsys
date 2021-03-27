#ifndef IXC_ROUTER_H
#define IXC_ROUTER_H

/// 表示一个ARP数据包
#define IXC_FLAG_ARP 0
/// 表示是一个DHCP CLIENT数据包
#define IXC_FLAG_DHCP_CLIENT 1
/// 表示是一个DHCP SERVER数据包
#define IXC_FLAG_DHCP_SERVER 2
/// 表示一个VSWITCH数据包
#define IXC_FLAG_VSWITCH 3
/// 表示一个Source filter数据包
#define IXC_FLAG_SRC_FILTER 4
/// 表示是一个带链路层头部的路由转发包
#define IXC_FLAG_ROUTE_FWD 5

#include<sys/types.h>

/// 发送数据到Python
// if_type 表示接口,该值来自于netif.h
// ipproto表示IP协议号,如果是链路层协议此参数为0
// flags 表示额外的参数补充
int ixc_router_send(unsigned char if_type,unsigned char ipproto,unsigned char flags,void *buf,size_t size);

/// 写入事件告知
int ixc_router_write_ev_tell(int fd,int flags);
/// 发送PPPoE数据包到Python
int ixc_router_pppoe_session_send(unsigned short protocol,unsigned short length,void *data);
/// 通知函数
int ixc_router_tell(const char *content);

#endif