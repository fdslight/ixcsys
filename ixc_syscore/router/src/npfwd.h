/*** 重定向网络数据包 ***/

#ifndef IXC_NPFWD_H
#define IXC_NPFWD_H

#include "mbuf.h"

#include "../../../pywind/clib/ev/ev.h"

#define IXC_NPFWD_INFO_MAX 10

struct ixc_npfwd_info{
    unsigned char key[16];
    int is_used;
    unsigned short port;
};

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

struct ixc_npfwd{
    struct ev_set *ev_set;
    int fileno;
};

int ixc_npfwd_init(struct ev_set *ev_set);
void ixc_npfwd_uninit(void);

/// 发生RAW的网络数据包
// fwd_flags为需要转发的类型
int ixc_npfwd_send_raw(struct ixc_mbuf *m,unsigned char ipproto,unsigned char flags);

/// 设置重定向
int ixc_npfwd_set_forward(unsigned char *key,unsigned short port,int flags);

#endif