/** 过滤指定机器的特定协议的流量 **/
#ifndef IXC_SRC_FILTER_H
#define IXC_SRC_FILTER_H

#include "mbuf.h"
#include "../../../pywind/clib/map.h"

struct ixc_src_filter{
    struct map *map;
    //unsigned char ip6_subnet[16];
    //unsigned char ip6_mask[16];

    //unsigned char ip_subnet[4];
    //unsigned char ip_mask[4];

    // 为0表示该协议直接跳过,非0表示过滤该数据
    unsigned char protocols[256];

    // 是否已经打开了src filter
    int is_opened;
};

int ixc_src_filter_init(void);
void ixc_src_filter_uninit(void);

int ixc_src_filter_enable(int enable);

int ixc_src_filter_add_hwaddr(const unsigned char *hwaddr);
void ixc_src_filter_del_hwaddr(const unsigned char *hwaddr);

//int ixc_src_filter_set_ip(unsigned char *subnet,unsigned char prefix,int is_ipv6);

/// 设置过滤协议
int ixc_src_filter_set_protocols(unsigned char *protocols);

void ixc_src_filter_handle(struct ixc_mbuf *m);


#endif