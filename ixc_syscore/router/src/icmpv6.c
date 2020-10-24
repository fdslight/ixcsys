#include<string.h>

#include "debug.h"
#include "icmpv6.h"
#include "mbuf.h"
#include "netif.h"
#include "ether.h"


/// 构建ICMPv6选项
// 注意length参数不包括option头部的type和length的值
static void ixc_icmpv6_opt_build(unsigned char type,unsigned char length,void *data,unsigned char *res)
{
    res[0]=type;
    res[1]=(length+2)/8;
    
    memcpy(&res[2],data,length);
}

static void ixc_icmpv6_handle_echo(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,struct netutil_icmpv6hdr *icmp_header)
{
    ixc_mbuf_put(m);
}

/// 处理路由请求报文
static void ixc_icmpv6_handle_rs(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,unsigned char icmp_code)
{
    struct ixc_netif *netif=m->netif;
    if(netif->type==IXC_NETIF_WAN || icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }
}

/// 处理路由宣告报文
static void ixc_icmpv6_handle_ra(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,unsigned char icmp_code)
{
    struct ixc_netif *netif=m->netif;
    if(netif->type==IXC_NETIF_LAN || icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }

    ixc_mbuf_put(m);
}

/// 处理邻居请求报文
static void ixc_icmpv6_handle_ns(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,unsigned char icmp_code)
{
    struct ixc_netif *netif=m->netif;
    if(icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }
    ixc_mbuf_put(m);
}

/// 处理另据宣告报文
static void ixc_icmpv6_handle_na(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,unsigned char icmp_code)
{
    struct ixc_netif *netif=m->netif;
    if(icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }
    ixc_mbuf_put(m);
}

void ixc_icmpv6_handle(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr)
{
    struct ixc_netif *netif=m->netif;
    struct netutil_icmpv6hdr *icmp_header;

    icmp_header=(struct netutil_icmpv6hdr *)(m->data+m->offset+40);

    if(icmp_header->type==128 || icmp_header->type==129){
        ixc_icmpv6_handle_echo(m,iphdr,icmp_header);
        return;
    }

    switch(icmp_header->type){
        case 133:
            ixc_icmpv6_handle_rs(m,iphdr,icmp_header->code);
            break;
        case 134:
            ixc_icmpv6_handle_ra(m,iphdr,icmp_header->code);
            break;
        case 135:
            ixc_icmpv6_handle_ns(m,iphdr,icmp_header->code);
            break;
        case 136:
            ixc_icmpv6_handle_na(m,iphdr,icmp_header->code);
            break;
        default:
            ixc_mbuf_put(m);
            break;
    }
}

int ixc_icmpv6_send_ra(void)
{
    return 0;
}

int ixc_icmpv6_send_rs(void)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    struct ixc_icmpv6_rs_header *icmp_header;
    struct ixc_mbuf *m;
    struct netutil_ip6hdr *ip6_hdr;
    struct netutil_ip6_ps_header *ps_header;
    unsigned char all_routers[]=IXC_ICMPv6_ALL_ROUTERS_ADDR;
    unsigned short csum;

    if(NULL==netif){
        STDERR("cannot get WAN network card\r\n");
        return -1;
    }

    m=ixc_mbuf_get();
    if(NULL==m){
        STDERR("cannot get mbuf or icmpv6 rs\r\n");
        return -1;
    }
    memcpy(m->src_hwaddr,netif->hwaddr,6);
    ixc_ether_get_multi_hwaddr_by_ipv6(all_routers,m->dst_hwaddr);

    m->netif=netif;
    m->next=NULL;
    m->link_proto=0x86dd;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=IXC_MBUF_BEGIN;

    icmp_header=(struct ixc_icmpv6_rs_header *)(m->data+m->offset);
    icmp_header->type=133;
    icmp_header->code=0;
    icmp_header->checksum=0;

    memset(icmp_header->reserved,0x00,4);

    ixc_icmpv6_opt_build(1,6,netif->hwaddr,m->data+m->offset+8);

    m->begin=m->offset;
    m->tail=m->begin+56;
    m->end=m->tail;

    ps_header=(struct netutil_ip6_ps_header *)(m->data+m->offset-40);
    bzero(ps_header,40);

    memcpy(ps_header->src_addr,netif->ip6_local_link_addr,16);
    memcpy(ps_header->dst_addr,all_routers,16);

    ps_header->length=htonl(16);
    ps_header->next_header=58;

    csum=csum_calc((unsigned short *)(m->data+m->offset-40),56);
    icmp_header->checksum=csum;

    ip6_hdr=(struct netutil_ip6hdr *)(m->data+m->offset-40);
    m->offset-=40;
    //csum_calc()
    IPv6_HEADER_SET(ip6_hdr,0,0,16,58,255,netif->ip6_local_link_addr,all_routers);

    DBG_FLAGS;

    ixc_ether_send(m,1);

    return 0;
}