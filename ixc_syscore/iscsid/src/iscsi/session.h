#ifndef IXC_ISCSI_SESSION_H
#define IXC_ISCSI_SESSION_H

#include "iscsi.h"

struct ixc_iscsi_session{
    
    char client_iqn[IXC_ISCSI_IQN_SIZE];
    char disk_iqn[IXC_ISCSI_IQN_SIZE];

};

#endif