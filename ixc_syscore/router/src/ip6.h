#ifndef IXC_IP6_H
#define IXC_IP6_H

/// 未指定地址
#define IXC_IP6ADDR_UNSPEC {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00}
/// loopback地址
#define IXC_IP6ADDR_LOOPBACK {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01}

/// 所有的路由器地址
#define IXC_IP6ADDR_ALL_ROUTERS {0xff,0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x02}
/// 所有的节点地址
#define IXC_IP6ADDR_ALL_NODES {0xff,0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01}
/// 请求节点多拨地址
#define IXC_IP6ADDR_SOL_NODE_MULTI {0xff,0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0xff,0x00,0x00,0x00}


#include "mbuf.h"

int ixc_ip6_init(void);
void ixc_ip6_uninit(void);

void ixc_ip6_handle(struct ixc_mbuf *mbuf);
int ixc_ip6_send(struct ixc_mbuf *mbuf);
int ixc_ip6_send_from_nm(struct ixc_mbuf *mbuf);

/// 获取EUI64规范名的后64位地址
int ixc_ip6_eui64_get(unsigned char *hwaddr,unsigned char *result);
/// 获取本地链路IPv6地址
int ixc_ip6_local_link_get(unsigned char *hwaddr,unsigned char *result);
/// 获取IPv6地址
// subnet为64位IPv6地址前缀
int ixc_ip6_addr_get(unsigned char *hwaddr,unsigned char *subnet,unsigned char *result);

/// 获取多播地址
int ixc_ip6_multi_brd_get(unsigned char *addr,unsigned char *result);

/// 开启或者关闭非系统DNS请求
int ixc_ip6_no_system_dns_drop_enable(int enable);

#endif