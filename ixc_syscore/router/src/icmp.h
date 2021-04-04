#ifndef IXC_ICMP_H
#define IXC_ICMP_H

#include "mbuf.h"

#include "../../../pywind/clib/netutils.h"

void ixc_icmp_handle_self(struct ixc_mbuf *m);
// 发送ICMP数据包,注意只能发送到内网,无法发送到WAN口
void ixc_icmp_send(unsigned char *saddr,unsigned char *daddr,struct netutil_icmphdr *icmphdr,void *data,size_t data_size);


#endif