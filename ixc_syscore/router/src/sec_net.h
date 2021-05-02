#ifndef IXC_SEC_NET_H
#define IXC_SEC_NET_H

#include<sys/time.h>

#include "mbuf.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/timer.h"

struct ixc_sec_net{
    // 规则
    struct map *rule_m;
};

struct ixc_sec_net_src_rule;
/// 目标规则器
struct ixc_sec_net_dst_rule{
    struct ixc_sec_net_src_rule *src_rule;
    struct ixc_sec_net_dst_rule *next;

    unsigned char address[16];
    unsigned char mask[16];
    // 缓存引用计数
    unsigned long long cache_refcnt;
    int action;
    unsigned char prefix; 
};

/// 源过滤器
struct ixc_sec_net_src_rule{
    struct ixc_sec_net_dst_rule *v4_dst_rule_head;
    struct ixc_sec_net_dst_rule *v6_dst_rule_head;
    // IPv4缓存
    struct map *ip_cache;
    // IPv6缓存
    struct map *ip6_cache;
    // 硬件地址
    unsigned char hwaddr[6];
    char pad[2];
    // 动作类型
    int action;
};

/// 缓存
struct ixc_sec_net_rule_cache{
    // 指向的目标规则
    struct ixc_sec_net_dst_rule *dst_rule;
    struct time_data *tdata;
    unsigned char address[16];
    time_t up_time;
    int action;
    int is_ipv6;
};

/// 丢弃数据包
#define IXC_SEC_NET_ACT_DROP 0
/// 接受数据包
#define IXC_SEC_NET_ACT_ACCEPT 1

/// 缓存超时时间
#define IXC_SEC_NET_CACHE_TIMEOUT 600


int ixc_sec_net_init(void);
void ixc_sec_net_uninit(void);

void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m);

/// 加入源端过滤规则
int ixc_sec_net_add_src(unsigned char *hwaddr,int action);
/// 删除源端过滤规则
void ixc_sec_net_del_src(unsigned char *hwaddr);

/// 加入目标过滤规则,注意删除只能删除src规则然后重新加入
int ixc_sec_net_add_dst(unsigned char *hwaddr,unsigned char *subnet,unsigned char prefix,int is_ipv6);


#endif