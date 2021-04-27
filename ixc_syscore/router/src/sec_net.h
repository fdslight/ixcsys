/* 实现IP网络安全,防止流氓软件等功能 **/

#ifndef IXC_SEC_NET_H
#define IXC_SEC_NET_H

#include<sys/types.h>

struct ixc_sec_net{
    
};

/// 安全IP记录
struct ixc_sec_net_log{
    unsigned char src_address[16];
    unsigned char dst_address[16];
    // 开始时间
    time_t begin;
    // 结束时间
    time_t end;
    // 访问次数
    unsigned long long acs_count;
    // 源硬件地址
    unsigned char src_hwaddr[6];
    // 目标硬件地址
    unsigned char dst_hwaddr[6];
    // ID号
    unsigned short id;
    // 协议号
    unsigned char protocol;
    // 填充字节
    unsigned char pad1[1];
    // 是否是IPv6
    int is_ipv6;
};


#endif