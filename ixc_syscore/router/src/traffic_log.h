#ifndef IXC_TRAFFIC_LOG_H
#define IXC_TRAFFIC_LOG_H

#include "ether.h"

struct ixc_traffic_log{
    // 主机硬件地址
    unsigned char hwaddr[6];
    // 是否是TCPIP协议
    char is_tcpip;
    // 是否是IPv6协议
    char is_ipv6;
    unsigned char host_addr[16];
    // 更新时间
    unsigned long long up_time;
    // 接收流量
    unsigned long long rx_traffic;
    // 发送流量
    unsigned long long tx_traffic;
};


int ixc_traffic_log_init(void);
void ixc_traffic_log_uninit(void);

/// 流量方向
#define IXC_TRAFFIC_LOG_DIR_OUT 0
///
#define IXC_TRAFFIC_LOG_DIR_IN 1
void ixc_traffic_log_statistics(struct ixc_ether_header *header,unsigned int size,int traffic_dir);
int ixc_traffic_log_enable(int enable);

#endif