/* iSCSI socket层 */
#ifndef IXC_ISOCKET_H
#define IXC_ISOCKET_H

struct ixc_isocket_session{
    unsigned char addr[32];
    // 目标卷名
    char iscsi_tgt[256];
    // 源卷名
    char iscsi_initiator[256];
    // 认证方式
    int auth_type;
    
    int fd;
};

/// 创建新的iSCSI会话
int _ixc_isocket_session_create(void);

/// 删除iSCSI会话
void _ixc_isocket_session_destroy(void);

int ixc_isocket_init(void);
void ixc_isocket_uninit(void);

void ixc_isocket_start_evloop(void);

#endif