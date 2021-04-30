/* 实现IP网络安全,防止流氓软件 */

#ifndef IXC_SEC_NET_H
#define IXC_SEC_NET_H

#include<sys/types.h>

#include "mbuf.h"

#include "../../../pywind/clib/map.h"

struct ixc_sec_net{
    struct map *rule_hwaddr_m;
    struct map *rule_ip_m;
    struct map *rule_ip6_m;
    // 硬件地址的log日志
    struct map *log_hwaddr_m;
    // IPv4的访问日志
    struct map *logv4_m;
    // IPv6的访问日志
    struct map *logv6_m;
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
    unsigned char hwaddr[6];
    // ID号
    unsigned short id;
    // 协议号
    unsigned char protocol;
    // 填充字节
    unsigned char pad1[3];
    // 引用计数
    unsigned int refcnt;
    // 是否是IPv6
    int is_ipv6;
};


/// 丢弃数据包
#define IXC_SEC_NET_ACT_DROP 0
/// 接受数据包
#define IXC_SEC_NET_ACT_ACCEPT 1

/// 目标地址过滤规则
struct ixc_sec_net_rule_dst{
    struct ixc_sec_net_rule_dst *next;
    unsigned char dst_addr[16];
    unsigned char mask[16];
    unsigned char prefix;
};

/// 源端过滤规则
// 如果IP地址不为0而硬件地址为0表示规则绑定IP地址
// 如果IP地址为0而MAC地址不为0表示绑定MAC地址
struct ixc_sec_net_rule_src{
    struct map *cache_m;
    struct ixc_sec_net_rule_dst *dst_head;
    // 源端IP地址,如果全零表示不绑定IP地址
    unsigned char address[16];
    short default_action;
    // 硬件地址,如果全0表示不绑定硬件地址
    unsigned char hwaddr[6];
    // 引用计数
    unsigned int refcnt;
    // 该值只有在源头
    int is_ipv6;
};

int ixc_sec_net_init(void);
void ixc_sec_net_uninit(void);

/// 源规则加入
int ixc_sec_net_src_rule_add(unsigned char *hwaddr,unsigned char *address,short action,int is_ipv6);
/// 源规则删除
int ixc_sec_net_src_rule_del(unsigned char *hwaddr,unsigned char *address,int is_ipv6);
/// 处理数据包
void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m);

#endif