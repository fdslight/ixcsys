#ifndef IXC_ISCSI_SESSION_H
#define IXC_ISCSI_SESSION_H

#include<arpa/inet.h>

int ixc_iscsi_session_create(int fd,void *sockaddr,socklen_t addrlen,int is_ipv6);
void ixc_iscsi_session_delete(void);

#endif