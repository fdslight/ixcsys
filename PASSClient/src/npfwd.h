/*** 重定向网络数据包 ***/

#ifndef IXC_NPFWD_H
#define IXC_NPFWD_H

#include "mbuf.h"

#include "../../pywind/clib/ev/ev.h"


struct ixc_npfwd_info{
    unsigned char key[16];
    unsigned char address[16];
    int is_used;
    unsigned short port;
    unsigned char pad[2];
};

#pragma pack(push)
#pragma pack(4)
/// 数据头部格式
struct ixc_npfwd_header{
    // key
    unsigned char key[16];
    // 要发送的网卡接口类型
    unsigned char if_type;
    // 填充字段
    unsigned char pad;
    // IP协议
    unsigned char ipproto;
    // 标志
    unsigned char flags;
};
#pragma pack(pop)

struct ixc_npfwd{
    struct ev_set *ev_set;
    struct ev *ev;
    int fileno;
};

int ixc_npfwd_init(struct ev_set *ev_set);
void ixc_npfwd_uninit(void);

int ixc_npfwd_send(struct ixc_mbuf *m);

int ixc_npfwd_set_forward(unsigned char *key,unsigned char *v4addr,unsigned short port);

#endif