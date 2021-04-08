#ifndef IXC_MBUF_H
#define IXC_MBUF_H

#include<sys/types.h>

#include "netif.h"
#include "../../../pywind/clib/debug.h"

#define IXC_MBUF_LOOP_TRACE_MAX_NUM 32

struct ixc_mbuf{
    struct ixc_mbuf *next;
    struct ixc_netif *netif;
    // 私有数据,用于处理IP包的一些功能,比如IP组包等等
    void *priv_data;
    // 私有标记,用于处理IP包的一些功能,比如IP组包等等
    int priv_flags;
    int is_ipv6;
    // 流量来自于哪里
    // 流量来自于LAN设备,包括local设备和tap设备以及从其他应用接收的数据包
#define IXC_MBUF_FROM_LAN 0
    // 流量来自于WAN网卡
#define IXC_MBUF_FROM_WAN 1
    // 来自于应用程序
#define IXC_MBUF_FROM_APP 2
    int from;
    // 开始位置
#define IXC_MBUF_BEGIN 512
    int begin;
    // 偏移位置
    int offset;
    // 尾部
    int tail;
    // 循环跟踪,造成死循环那么给予警告
    int loop_trace;
    // 结束位置
#define IXC_MBUF_END 0xffff
    int end;
    // 是否开启透传
    int passthrough;
    
    union{
        unsigned short link_proto;
        unsigned char ipproto;
    };

    // 指向的下一条主机
    unsigned char next_host[16];
#define IXC_MBUF_DATA_MAX_SIZE 0x101ff
    unsigned char data[IXC_MBUF_DATA_MAX_SIZE];
    unsigned char src_hwaddr[6];
    unsigned char dst_hwaddr[6];
};

/// 检查是否造成了死循环
#ifdef DEBUG
#define IXC_MBUF_LOOP_TRACE(M) \
if(M->loop_trace > IXC_MBUF_LOOP_TRACE_MAX_NUM){\
    STDERR("network packet endless loop\r\n");\
    ixc_mbuf_put(M);\
}
#else
#define IXC_MBUF_LOOP_TRACE(M)
#endif

int ixc_mbuf_init(size_t pre_alloc_num);
void ixc_mbuf_uninit(void);

struct ixc_mbuf *ixc_mbuf_get(void);
void ixc_mbuf_put(struct ixc_mbuf *m);
/// 克隆mbuf
struct ixc_mbuf *ixc_mbuf_clone(struct ixc_mbuf *m);

#endif