#ifndef IXC_ICMP_H
#define IXC_ICMP_H

#include "mbuf.h"

#include "../../../pywind/clib/netutils.h"

void ixc_icmp_handle_self(struct ixc_mbuf *m);
/// 发送ICMP数据包,注意只能发送到内网,无法发送到WAN口
void ixc_icmp_send(unsigned char *saddr,unsigned char *daddr,struct netutil_icmphdr *icmphdr,void *data,unsigned short data_size);

/// 发送ICMP time exceeded message
void ixc_icmp_send_time_ex_msg(unsigned char *saddr,unsigned char *daddr,unsigned char code,void *data,unsigned short data_size);

#endif