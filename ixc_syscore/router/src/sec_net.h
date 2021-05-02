#ifndef IXC_SEC_NET_H
#define IXC_SEC_NET_H

#include<sys/time.h>

#include "mbuf.h"

#include "../../../pywind/clib/map.h"

struct ixc_sec_net{
    // IPv4日志
    struct map *logv4m;
    // IPv6日志
    struct map *logv6m;
    // IPv4缓存
    struct map *cache_m;
    // IPv6缓存
    struct map *cache6_m;
    // 规则
    struct map *rule;
};

struct ixc_sec_net_log{
    unsigned char address[16];
    // 访问计数
    unsigned long long acs_count;
    unsigned char hwaddr[6];
    // 访问的协议类型
    unsigned short id;
    time_t up_time;
    // 开始时间
    time_t begin_time;
    int is_ipv6;
    // 访问的协议类型
    unsigned char protocol;
};

struct ixc_sec_net_src_rule_L2;

/// 目标规则器
struct ixc_sec_net_dst_rule{
    struct ixc_sec_net_src_rule_L2 *src_L2_rule;
    struct ixc_sec_net_dst_rule *next;

    unsigned char address[16];
    unsigned char mask[16];
    // 是否已经删除
    int is_deleted;
    unsigned char prefix; 
};

/// 一级过滤器
struct ixc_sec_net_src_rule_L1{
    struct map *ip_m;
    struct map *ip6_m;
    unsigned char hwaddr[6];
    char pad[2];
    // 动作类型
    int action;
};

/// 二级源端过滤器
struct ixc_sec_net_src_rule_L2{
    struct ixc_sec_src_rule_L1 *L1_rule;
    struct ixc_sec_net_dst_rule *dst_rule_head;

    unsigned char address[16];
    int action;
    int is_ipv6;
};


/// 丢弃数据包
#define IXC_SEC_NET_ACT_DROP 0
/// 接受数据包
#define IXC_SEC_NET_ACT_ACCEPT 1


int ixc_sec_net_init(void);
void ixc_sec_net_uninit(void);

void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m);


#endif