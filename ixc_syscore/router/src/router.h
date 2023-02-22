#ifndef IXC_ROUTER_H
#define IXC_ROUTER_H

// 系统阻塞IO等待时间,请不要修改这个值,否则可能造成内存错误
#define IXC_IO_WAIT_TIMEOUT 10

/// 表示一个ARP数据包
#define IXC_FLAG_ARP 0
/// 表示是一个DHCP CLIENT数据包
#define IXC_FLAG_DHCP_CLIENT 1
/// 表示是一个DHCP SERVER数据包
#define IXC_FLAG_DHCP_SERVER 2
/// 表示一个Source filter数据包
#define IXC_FLAG_SRC_FILTER 3
/// 路由转发包
#define IXC_FLAG_ROUTE_FWD 4

#include<sys/types.h>

/// 发送PPPoE数据包到Python
int ixc_router_pppoe_session_send(unsigned short protocol,unsigned short length,void *data);
/// 通知函数
int ixc_router_tell(const char *content);

void ixc_router_exit(void);

void ixc_router_md5_calc(void *data,int size,unsigned char *res);

#endif