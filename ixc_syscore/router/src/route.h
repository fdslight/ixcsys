#ifndef IXC_ROUTE_H
#define IXC_ROUTE_H

#include "mbuf.h"
#include "netif.h"

#include "../../../pywind/clib/map.h"

/// 保存前缀信息
struct ixc_route_prefix{
    struct ixc_route_prefix *next;
    // 该前缀被引用的次数
    unsigned long long refcnt;
    unsigned char mask[16];
    unsigned char prefix;
};

struct ixc_route_info{
    // 指向的设备
    struct ixc_netif *netif;
    unsigned char subnet[16];
    // 指向的网关
    unsigned char gw[16];
    // 是否需要以链路层形式发送
    int is_linked;
    int is_ipv6;
    unsigned char prefix;
};

struct ixc_route{
    struct map *ip_rt;
    struct map *ip6_rt;
    struct ixc_route_prefix *ip_pre_head;
    struct ixc_route_prefix *ip6_pre_head;
};

int ixc_route_init(void);
void ixc_route_uninit(void);

/// 增加路由
// 如果gw参数为NULL则代表该数据发向其他应用的路由
int ixc_route_add(unsigned char *subnet,unsigned char prefix,unsigned char *gw,int is_ipv6,int is_linked);
void ixc_route_del(unsigned char *subnet,unsigned char prefix,int is_ipv6);
/// 匹配路由
struct ixc_route_info *ixc_route_match(unsigned char *ip,int is_ipv6);
/// 获取路由
struct ixc_route_info *ixc_route_get(unsigned char *subnet,unsigned char prefix,int is_ipv6);

void ixc_route_handle(struct ixc_mbuf *m);

#endif