#ifndef IXC_PPPOE_H
#define IXC_PPPOE_H

#include "mbuf.h"

#pragma pack(push)
#pragma pack(1)
struct ixc_pppoe_header{
    unsigned char ver_and_type;
    /// PPPOE 会话相关代码
#define IXC_PPPOE_CODE_SESSION 0x00
#define IXC_PPPOE_CODE_PADI 0x09
#define IXC_PPPOE_CODE_PADO 0x07
#define IXC_PPPOE_CODE_PADR 0x19
#define IXC_PPPOE_CODE_PADS 0x65
    unsigned char code;

    unsigned short session_id;
    unsigned short length;
};

/// PPPoE tag描述
struct ixc_pppoe_tag_header{
    unsigned short type;
    unsigned short length;
};

#pragma pack(pop)

struct ixc_pppoe{
    // 是否开启PPPoE会话
    int is_started;
    // pppoe会话是否成功
    int pppoe_ok;
    // 是否开启PPPoE会话
    int enable;
    // PPPoE的用户名
    char username[512];
    // PPPoE的密码
    char passwd[512];
    // 当前会话阶段
    unsigned char cur_session_step;
};

int ixc_pppoe_init(void);
void ixc_pppoe_uninit(void);

///  设置PPPOE的用户名和密码
int ixc_pppoe_set_user(char *username,char *passwd);

/// 开始进行PPPoE的会话
void ixc_pppoe_start(void);
/// 停止PPPoE的会话
void ixc_pppoe_stop(void);

/// 把数据包发送PPPOE进行处理
void ixc_pppoe_handle(struct ixc_mbuf *m);

/// 检查PPPoE是否握手成功
int ixc_pppoe_ok(void);

/// 启用PPPoE
int ixc_pppoe_enable(int status);

#endif