#ifndef IXC_ISCSI_SESSION_H
#define IXC_ISCSI_SESSION_H

#include "iscsi.h"
#include "../mbuf.h"

#define IXC_ISCSI_ST_HADNSHAKE 0
#define IXC_ISCSI_ST_DISK_T 1

struct ixc_iscsi_session{
    
    char client_iqn[IXC_ISCSI_IQN_SIZE];
    char disk_iqn[IXC_ISCSI_IQN_SIZE];
};

int ixc_iscsi_session_init(void);
int ixc_iscsi_session_handle_request(struct ixc_mbuf *m);
void ixc_iscsi_session_uninit(void);

#endif