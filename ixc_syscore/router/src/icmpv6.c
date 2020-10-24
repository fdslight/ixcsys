#include<string.h>

#include "debug.h"
#include "icmpv6.h"
#include "mbuf.h"
#include "netif.h"
#include "ether.h"

static int ixc_icmpv6_send(struct ixc_netif *netif,unsigned char *dst_hwaddr,unsigned char *src_ipaddr,unsigned char *dst_ipaddr,void *icmp_data,int length)
{
    struct ixc_mbuf *m=ixc_mbuf_get();
    struct netutil_icmpv6hdr *icmpv6_header=icmp_data;
    struct netutil_ip6_ps_header *ps_header;
    struct netutil_ip6hdr *ip6hdr;

    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        ixc_mbuf_put(m);
        return -1;
    }

    m->next=NULL;
    m->netif=netif;
    m->link_proto=0x86dd;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=IXC_MBUF_BEGIN;
    
    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memcpy(m->dst_hwaddr,dst_hwaddr,6);

    ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset-40);
    ps_header=(struct netutil_ip6_ps_header *)(m->data+m->offset-40);

    bzero(ps_header,40);

    memcpy(ps_header->src_addr,src_ipaddr,16);
    memcpy(ps_header->dst_addr,dst_ipaddr,16);

    ps_header->length=htonl(length);
    ps_header->next_header=58;

    memcpy(m->data+m->offset,icmp_data,length);

    icmpv6_header=(struct netutil_icmpv6hdr *)(m->data+m->offset);
    icmpv6_header->checksum=0;
    icmpv6_header->checksum=csum_calc((unsigned short *)(m->data+m->offset-40),length+40);

    IPv6_HEADER_SET(ip6hdr,0,0,16,58,255,src_ipaddr,dst_ipaddr);

    m->tail=m->offset+length;
    m->end=m->tail;

    m->offset=m->offset-40;
    m->begin=m->offset;

    ixc_ether_send(m,1);

    return 0;
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
    struct ixc_icmpv6_ns_header *ns_hdr=NULL;
    struct ixc_icmpv6_opt_link_addr *ns_opt,*na_opt;
    struct ixc_icmpv6_na_header *na_header;

    unsigned char buf[32];
    unsigned int rso=0;

    if(icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }

    if(m->tail-m->offset!=32){
        ixc_mbuf_put(m);
        return;
    }

    ns_hdr=(struct ixc_icmpv6_ns_header *)(m->data+m->offset);
    ns_opt=(struct ixc_icmpv6_opt_link_addr *)(m->data+m->offset+24);
    // 不是本机器的地址那么丢弃数据包
    if(memcmp(netif->ip6addr,ns_hdr->target_addr,16)){
        ixc_mbuf_put(m);
        return;
    }

    bzero(buf,32);

    na_header=(struct ixc_icmpv6_na_header *)buf;
    na_opt=(struct ixc_icmpv6_opt_link_addr *)(&buf[24]);


    if(netif->type==IXC_NETIF_LAN){
        rso=rso | (0x00000001 << 31);
    }

    rso=rso | (0x00000001<<29);
    na_header->type=136;
    na_header->code=0;
    na_header->rso=htonl(rso);

    na_opt->type=2;
    na_opt->length=1;

    ixc_icmpv6_send(netif,m->src_hwaddr,netif->ip6addr,iphdr->src_addr,buf,32);

    ixc_mbuf_put(m);
}

/// 处理邻居宣告报文
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

    // 检查格式是否正确
    if(iphdr->hop_limit!=255){
        ixc_mbuf_put(m);
        return;
    }

    // 指向到ICMP头部
    m->offset+=40;

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
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);
    struct ixc_icmpv6_ra_header *ra_header;
    struct ixc_icmpv6_opt_ra *ra_opt;
    unsigned char all_routers[]=IXC_ICMPv6_ALL_ROUTERS_ADDR;
    unsigned char dst_hwaddr[6];

    unsigned char buf[64];
    bzero(buf,64);

    ra_header=(struct ixc_icmpv6_ra_header *)buf;
    ra_opt=(struct ixc_icmpv6_opt_ra *)(&buf[16]);

    ra_header->type=134;
    ra_header->code=0;
    ra_header->checksum=0;
    ra_header->router_lifetime=htons(3600);

    ra_opt->type_hwaddr=1;
    ra_opt->length_hwaddr=1;
    memcpy(ra_opt->hwaddr,netif->hwaddr,6);

    ra_opt->type_mtu=5;
    ra_opt->length_mtu=1;
    ra_opt->mtu=htons(1280);

    ra_opt->type_prefix=3;
    ra_opt->length_prefix=4;
    ra_opt->prefix_length=64;
    ra_opt->prefix_flags=0x40;
    ra_opt->prefix_valid_lifetime=0xffffffff;
    ra_opt->prefix_preferred_lifetime=0xffffffff;
    memcpy(ra_opt->prefix,netif->ip6_subnet,16);

    ixc_ether_get_multi_hwaddr_by_ipv6(all_routers,dst_hwaddr);
    ixc_icmpv6_send(netif,dst_hwaddr,netif->ip6_local_link_addr,all_routers,buf,64);

    return 0;
}

int ixc_icmpv6_send_rs(void)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    struct ixc_icmpv6_rs_header *icmp_header;
    struct ixc_icmpv6_opt_link_addr *opt;

    unsigned char all_routers[]=IXC_ICMPv6_ALL_ROUTERS_ADDR;
    unsigned char dst_hwaddr[6];
    unsigned char buf[16];

    if(NULL==netif){
        STDERR("cannot get WAN network card\r\n");
        return -1;
    }
    bzero(buf,16);

    icmp_header=(struct ixc_icmpv6_rs_header *)buf;
    opt=(struct ixc_icmpv6_opt_link_addr *)(&buf[8]);

    icmp_header->type=133;
    icmp_header->code=0;
    icmp_header->checksum=0;

    opt->type=1;
    opt->length=1;

    memcpy(opt->hwaddr,netif->hwaddr,6);

    ixc_ether_get_multi_hwaddr_by_ipv6(all_routers,dst_hwaddr);
    ixc_icmpv6_send(netif,dst_hwaddr,netif->ip6_local_link_addr,all_routers,buf,16);

    DBG_FLAGS;

    return 0;
}