#ifndef IXC_TCP_LISTENER_H
#define IXC_TCP_LISTENER_H

#include "../../../pywind/clib/ev/ev.h"

int ixc_tcp_listener_init(const char *addr,int enable_ipv6);
void ixc_tcp_listener_uninit(void);

#endif