#ifndef IP2SOCKS_IP_H
#define IP2SOCKS_IP_H

#include "mbuf.h"

void ip_handle(struct mbuf *m);

int ip_send(unsigned char *src_addr,unsigned char *dst_addr,unsigned char protocol,struct mbuf *m);

#endif