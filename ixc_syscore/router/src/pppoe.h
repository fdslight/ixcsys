#ifndef IXC_PPPOE_H
#define IXC_PPPOE_H

#include<time.h>

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
#define IXC_PPPOE_CODE_PADT 0xa7
    unsigned char code;

    unsigned short session_id;
    unsigned short length;
};

/// PPPoE tag描述
struct ixc_pppoe_tag{
    // 下一个PPPoE TAG标签
    struct ixc_pppoe_tag *next;

    unsigned short type;
    unsigned short length;
    unsigned char data[1500];
};

struct ixc_pppoe_tag_header{
    unsigned short type;
    unsigned short length;
};

#pragma pack(pop)

struct ixc_pppoe{
    time_t up_time;
    // 是否开启PPPoE会话
    int is_started;
    // pppoe会话是否成功
    int pppoe_ok;
    // 是否开启PPPoE会话
    int enable;
    // PPPoE discovery 是否成功
    int discovery_ok;
    // 是否选择了服务器
    int is_selected_server;
    int ac_cookie_len;
    // PPPoE的用户名
    char username[512];
    // PPPoE的密码
    char passwd[512];
    char ac_name[2048];
    unsigned char ac_cookie[2048];
    unsigned short session_id;
    // 选择的PPPoE服务器
    unsigned char selected_server_hwaddr[6];
    // 当前PPPoE发现阶段
    unsigned char cur_discovery_stage;
};

int ixc_pppoe_init(void);
void ixc_pppoe_uninit(void);

///  设置PPPOE的用户名和密码
int ixc_pppoe_set_user(const char *username,const char *passwd);

/// 开始进行PPPoE的会话
void ixc_pppoe_start(void);
/// 停止PPPoE的会话
void ixc_pppoe_stop(void);

/// 把数据包发送PPPOE进行处理
void ixc_pppoe_handle(struct ixc_mbuf *m);

/// 设置pppoe ok
void ixc_pppoe_set_ok(int ok);

/// 启用PPPoE
int ixc_pppoe_enable(int status);

/// PPPoE是否启用
int ixc_pppoe_is_enabled(void);
/// 发送PPPoE数据包
void ixc_pppoe_send(struct ixc_mbuf *m);
/// 发送PPPoE session数据包
void ixc_pppoe_send_session_packet(unsigned short ppp_protocol,unsigned short length,void *data);

/// 重置PPPoE会话
void ixc_pppoe_reset(void);

struct ixc_pppoe *ixc_pppoe(void);
void ixc_pppoe_send_pap_user(void);

#endif