#ifndef IXC_ROUTE_H
#define IXC_ROUTE_H

#include "mbuf.h"
#include "netif.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/timer.h"

/// 路由缓存超时时间
#define IXC_ROUTE_CACHE_TIMEOUT 1200

/// 保存前缀信息
struct ixc_route_prefix{
    struct ixc_route_prefix *next;
    // 该前缀被引用的次数
    unsigned long long refcnt;
    unsigned char mask[16];
    unsigned char pad[7];
    unsigned char prefix;
};

struct ixc_route_info{
    // 指向的设备
    struct ixc_netif *netif;
    unsigned char subnet[16];
    // 指向的网关
    unsigned char gw[16];
    int is_ipv6;
    // 该路由是否已经无效
    int is_invalid;
    // 路由是否已经被缓存
    int is_cached;
    unsigned char pad[3];
    unsigned char prefix;
};

struct ixc_route_cache{
	struct ixc_route_info *r_info;
    struct time_data *tdata;
	// 缓存地址
	unsigned char address[16];
	int is_ipv6;
};

struct ixc_route{
    struct map *ip_rt;
    struct map *ip6_rt;
    // IPv4路由缓存
    struct map *ip_rt_cache;
    // IPv6路由缓存
    struct map *ip6_rt_cache;
    struct ixc_route_prefix *ip_pre_head;
    struct ixc_route_prefix *ip6_pre_head;
    // 是否开启IPv6透传
    int ipv6_pass;
};

int ixc_route_init(void);
void ixc_route_uninit(void);

/// 增加路由
// 如果gw参数为NULL则代表该数据发向其他应用的路由
int ixc_route_add(unsigned char *subnet,unsigned char prefix,unsigned char *gw,int is_ipv6);
void ixc_route_del(unsigned char *subnet,unsigned char prefix,int is_ipv6);
/// 匹配路由
struct ixc_route_info *ixc_route_match(unsigned char *ip,int is_ipv6);
/// 获取路由
struct ixc_route_info *ixc_route_get(unsigned char *subnet,unsigned char prefix,int is_ipv6);

void ixc_route_handle(struct ixc_mbuf *m);
/// 是否开启了IPv6透传
int ixc_route_is_enabled_ipv6_pass(void);
/// 启用或者关闭IPv6透传
int ixc_route_ipv6_pass_enable(int enable);

#endif
