#ifndef IP2SOCKS_IPv6_H
#define IP2SOCKS_IPv6_H

#include "mbuf.h"

void ipv6_handle(struct mbuf *m);

int ipv6_send(unsigned char *src_addr,unsigned char *dst_addr,unsigned char protocol,struct mbuf *m);

#endif