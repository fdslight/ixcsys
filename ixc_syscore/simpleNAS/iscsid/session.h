#ifndef IXC_ISCSI_SESSION_H
#define IXC_ISCSI_SESSION_H

int ixc_iscsi_session_create(void *sockaddr,int is_ipv6);
void ixc_iscsi_session_uninit(void);


#endif