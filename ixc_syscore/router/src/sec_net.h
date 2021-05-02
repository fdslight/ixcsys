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
    // 规则
    struct map *rule_m;
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

struct ixc_sec_net_src_rule;
/// 目标规则器
struct ixc_sec_net_dst_rule{
    struct ixc_sec_net_src_rule *src_rule;
    struct ixc_sec_net_dst_rule *next;

    unsigned char address[16];
    unsigned char mask[16];
    // 缓存引用计数
    unsigned long long cache_refcnt;
    // 是否已经删除
    int is_deleted;
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
    // 是否删除
    int is_deleted;
};

/// 缓存
struct ixc_sec_net_rule_cache{
    // 指向的目标规则
    struct ixc_sec_net_dst_rule *dst_rule;
    unsigned char address[16];
    time_t up_time;
    int action;
};

/// 丢弃数据包
#define IXC_SEC_NET_ACT_DROP 0
/// 接受数据包
#define IXC_SEC_NET_ACT_ACCEPT 1


int ixc_sec_net_init(void);
void ixc_sec_net_uninit(void);

void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m);

/// 加入源端过滤规则
int ixc_sec_net_add_src(unsigned char *hwaddr,int action);
/// 删除源端过滤规则
void ixc_sec_net_del_src(unsigned char *hwaddr);

/// 加入目标过滤规则
int ixc_sec_net_add_dst(unsigned char *hwaddr,unsigned char *subnet,unsigned char prefix,int is_ipv6);
/// 删除目标过滤规则
void ixc_sec_net_del_dst(unsigned char *hwaddr,unsigned char *subnet,unsigned char prefix,int is_ipv6);


#endif