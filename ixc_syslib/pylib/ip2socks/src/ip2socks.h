#ifndef IP2SOCKS_H
#define IP2SOCKS_H

#include "mbuf.h"

struct proto_info{
    // 字符串源地址
    char src_addr[256];
    // 字符串目的地址
    char dst_addr[256];
    // 源端口
    unsigned short src_port;
    // 目标端口
    unsigned short dst_port;
    // 协议
    unsigned char protocol;
    char pad[3];
    // 是否是IPv6协议
    int is_ipv6;
};

/// 装饰成IP数据包
struct mbuf *wrap_to_ippkt(struct proto_info *info,void *app_data,int size);


#endif