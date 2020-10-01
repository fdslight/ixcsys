#include<string.h>

#include "udp_src_filter.h"
#include "qos.h"
#include "netif.h"
#include "router.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_udp_src_filter udp_src_filter;

static void ixc_udp_src_filter_send(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;
    int is_not_subnet;
    unsigned char result[16];
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    unsigned char ipproto=0;

    // 只处理LAN网卡
    if(IXC_NETIF_LAN!=netif->type){
        ixc_qos_add(m);
        return;
    }

    if(m->is_ipv6) {
        ipproto=ip6hdr->next_header;
        if(ipproto!=17 || ipproto!=136){
            ixc_qos_add(m);
            return;
        }
        subnet_calc_with_msk(ip6hdr->src_addr,udp_src_filter.ip6_mask,1,result);
        is_not_subnet=memcmp(udp_src_filter.ip6_subnet,result,16);
        
    }else{
        ipproto=iphdr->protocol;
        if(ipproto!=17 || ipproto!=136){
            ixc_qos_add(m);
            return;
        }
        subnet_calc_with_msk(iphdr->src_addr,udp_src_filter.ip_mask,0,result);
        is_not_subnet=memcmp(udp_src_filter.ip_subnet,result,4);
    }

    // 不在要求的地址范围内那么直接发送到下一个节点
    if(is_not_subnet){
        ixc_qos_add(m);
        return;
    }

    if(udp_src_filter.is_linked) ixc_router_send(netif->type,0,IXC_FLAG_SRC_UDP_FILTER,m->data+m->begin,m->end-m->begin);
    else ixc_router_send(netif->type,ipproto,IXC_FLAG_SRC_UDP_FILTER,m->data+m->offset,m->tail-m->offset);
}

int ixc_udp_src_filter_init(void)
{
    bzero(&udp_src_filter,sizeof(struct ixc_udp_src_filter));
    return 0;
}

void ixc_udp_src_filter_uninit(void)
{
    udp_src_filter.is_opened=0;
}

int ixc_udp_src_filter_enable(int enable,int is_linked)
{
    udp_src_filter.is_opened=enable;
    udp_src_filter.is_linked=is_linked;

    return 0;
}

int ixc_udp_src_filter_set_ip(unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    unsigned char result[16];
    int size=is_ipv6?16:4;
    subnet_calc_with_prefix(subnet,prefix,is_ipv6,result);

    if(memcmp(subnet,result,size)) return -1;

    if(is_ipv6){
        memcpy(udp_src_filter.ip6_subnet,subnet,16);
        msk_calc(prefix,1,udp_src_filter.ip6_mask);
    }else{
        memcpy(udp_src_filter.ip_subnet,subnet,4);
        msk_calc(prefix,0,udp_src_filter.ip_mask);
    }

    return 0;
}

void ixc_udp_src_filter_handle(struct ixc_mbuf *m)
{
    // 如果没启用P2P那么直接发送数据
    if(!udp_src_filter.is_opened) ixc_qos_add(m);
    else ixc_udp_src_filter_send(m);
}