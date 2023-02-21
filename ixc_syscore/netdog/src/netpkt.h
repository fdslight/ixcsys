/*网络包接收,接收路由器镜像过来的数据包*/
#ifndef IXC_NETPKT_H
#define IXC_NETPKT_H

#include "mbuf.h"
#include "../../../pywind/clib/ev/ev.h"

#pragma pack(push)
#pragma pack(4)
/// 数据头部格式
struct ixc_netpkt_header{
    // key
    unsigned char key[16];
#define IXC_NETIF_LAN 0
#define IXC_NETIF_WAN 1
    // 要发送的网卡接口类型
    unsigned char if_type;
    // 填充字段
    unsigned char pad;
    // IP协议
    unsigned char ipproto;
    // 标志
    unsigned char flags;
    // 版本号,当前固定值为1
    unsigned char version;
    // 流量方向
    // 输出流量
#define IXC_TRAFFIC_OUT 0
    // 接收流量
#define IXC_TRAFFIC_IN 1
    unsigned char traffic_dir;
    char pad2[6];
    // 数据包的时间（秒）
    unsigned long long sec_time;
    // 数据包的时间（微秒）
    unsigned long long usec_time;
};
#pragma pack(pop)

int ixc_netpkt_init(struct ev_set *ev_set);
void ixc_netpkt_uninit(void);

// 获取通信端口
int ixc_netpkt_port_get(unsigned short *port);
// 获取通信key
int ixc_netpkt_key_get(unsigned char *res);
// 发送链路层据包
void ixc_netpkt_send(struct ixc_mbuf *m);
// 是否有数据包
int ixc_netpkt_have(void);
void ixc_netpkt_loop(void);

#endif