#ifndef IXC_ADDR_MAP_H
#define IXC_ADDR_MAP_H

#include<time.h>

#include "netif.h"
#include "mbuf.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/timer.h"

#define IXC_ADDR_MAP_TIMEOUT 600

struct ixc_addr_map{
    struct map *ip_record;
    struct map *ip6_record;
    struct time_wheel time_wheel;
};

struct ixc_addr_map_record{
    struct ixc_netif *netif;
    struct time_data *tdata;
    unsigned char address[16];
    time_t up_time;
    int is_ipv6;
    int is_changed;
    unsigned char hwaddr[6];
};

int ixc_addr_map_init(void);
void ixc_addr_map_uninit(void);

struct ixc_addr_map_record *ixc_addr_map_get(unsigned char *ip,int is_ipv6);

int ixc_addr_map_add(struct ixc_netif *netif,unsigned char *ip,unsigned char *hwaddr,int is_ipv6);
struct ixc_addr_map_record *ixc_addr_map_get(unsigned char *ip,int is_ipv6);
void ixc_addr_map_handle(struct ixc_mbuf *m);

///核对地址,检查客户端是否改变了地址
int ixc_addr_map_check(unsigned char *ip,unsigned char *hwaddr,int is_ipv6);

#endif