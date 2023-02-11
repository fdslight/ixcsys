#ifndef IXC_ISCSI_NET_WORKER_H
#define IXC_ISCSI_NET_WORKER_H

#include<sys/types.h>
#include<arpa/inet.h>

#include "../../../pywind/clib/ev/ev.h"

int ixc_net_worker_start(int client_fd,struct sockaddr *client_addr,socklen_t client_addrlen,int is_ipv6);
void ixc_net_worker_evloop(void);

#endif