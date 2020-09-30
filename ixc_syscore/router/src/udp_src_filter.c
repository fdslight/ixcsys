#include<string.h>

#include "udp_src_filter.h"
#include "ether.h"
#include "nat.h"
#include "natv6.h"

#include "../../../pywind/clib/debug.h"

static int udp_src_filter_enable=0;
static struct ixc_udp_src_filter udp_src_filter;

static void ixc_udp_src_filter_send(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;

    // 只处理LAN网卡
    if(IXC_NETIF_LAN==netif->type){
        // 检查是否在指定的地址范围内
    }

    if(m->is_ipv6) ixc_natv6_handle(m);
    else ixc_nat_handle(m);
}

int ixc_udp_src_filter_init(void)
{
    bzero(&udp_src_filter,sizeof(struct ixc_udp_src_filter));
    return 0;
}

void ixc_udp_src_filter_uninit(void)
{
    
}

int ixc_udp_src_filter_enable(int enable,int is_linked)
{
    return 0;
}

int ixc_udp_src_filter_set(unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    return 0;
}

void ixc_udp_src_filter_handle(struct ixc_mbuf *m)
{
    // 如果没启用P2P那么直接发送数据
    if(!udp_src_filter_enable) ixc_udp_src_filter_send(m);
}