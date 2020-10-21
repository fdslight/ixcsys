#ifndef IXC_IP6_H
#define IXC_IP6_H

#include "mbuf.h"

void ixc_ip6_handle(struct ixc_mbuf *mbuf);
int ixc_ip6_send(struct ixc_mbuf *mbuf);

/// 获取EUI64规范名的后64位地址
int ixc_ip6_eui64_get(unsigned char *hwaddr,unsigned char *result);
/// 获取本地链路IPv6地址
int ixc_ip6_local_link_get(unsigned char *hwaddr,unsigned char *result);
/// 获取IPv6地址
// subnet为64位IPv6地址前缀
int ixc_ip6_addr_get(unsigned char *hwaddr,unsigned char *subnet,unsigned char *result);

#endif