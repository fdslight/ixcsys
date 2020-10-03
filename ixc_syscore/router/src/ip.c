#include<arpa/inet.h>
#include<string.h>

#include "ip.h"
#include "ip6.h"
#include "netif.h"
#include "route.h"
#include "icmp.h"
#include "addr_map.h"
#include "ether.h"
#include "router.h"
#include "nat.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/debug.h"

static void ixc_ip_handle_icmp(struct ixc_mbuf *m,struct netutil_iphdr *header)
{
    struct ixc_netif *netif=m->netif;

    // 不是发送本机的ICMP直接发送到路由
    if(memcmp(netif->ipaddr,header->dst_addr,4)){
        ixc_route_handle(m);
        return;
    }

    ixc_icmp_handle(m,1);
}


static void ixc_ip_handle_from_wan(struct ixc_mbuf *m,struct netutil_iphdr *iphdr)
{
    struct netutil_udphdr *udphdr;
    int hdr_len=(iphdr->ver_and_ihl & 0x0f) *4;

    if(1==iphdr->protocol){
        ixc_ip_handle_icmp(m,iphdr);
        return;
    }
    
    if(17!=iphdr->protocol){
        ixc_mbuf_put(m);
        return;
    }

    udphdr=(struct netutil_udphdr *)(m->data+m->offset+hdr_len);

    // 检查是DHCP client报文并且开启DHCP的那么处理DHCP报文
    if(ntohs(udphdr->dst_port)==68 && ntohs(udphdr->src_port)==67){
        ixc_router_send(IXC_NETIF_WAN,0,IXC_FLAG_DHCP_CLIENT,m->data+m->begin,m->end-m->begin);
        return;
    }

    ixc_nat_handle(m);
}

static void ixc_ip_handle_from_lan(struct ixc_mbuf *m,struct netutil_iphdr *iphdr)
{
    struct netutil_udphdr *udphdr;
    int hdr_len=(iphdr->ver_and_ihl & 0x0f) *4;

    if(1==iphdr->protocol){
        ixc_ip_handle_icmp(m,iphdr);
        return;
    }

    udphdr=(struct netutil_udphdr *)(m->data+m->offset+hdr_len);

    // 检查是DHCP client报文并且开启DHCP的那么处理DHCP报文
    if(ntohs(udphdr->dst_port)==67 && ntohs(udphdr->src_port)==68){
        ixc_router_send(IXC_NETIF_LAN,0,IXC_FLAG_DHCP_SERVER,m->data+m->begin,m->end-m->begin);
        return;
    }

    // 发送数据到router
    ixc_route_handle(m);
}


void ixc_ip_handle(struct ixc_mbuf *mbuf)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(mbuf->data+mbuf->offset);
    int version=(header->ver_and_ihl & 0xf0) >> 4;
    unsigned short tot_len;
    struct ixc_netif *netif=mbuf->netif;

    if(4!=version){
        ixc_mbuf_put(mbuf);
        return;
    }

    //STDERR("%d.%d.%d.%d\r\n",header->dst_addr[0],header->dst_addr[1],header->dst_addr[2],header->dst_addr[3]);

    // 首先检查IP长度是否合法
    tot_len=ntohs(header->tot_len);

    if(tot_len > mbuf->tail- mbuf->offset){
        ixc_mbuf_put(mbuf);
        return;
    }

    mbuf->is_ipv6=0;
    // 除去以太网的填充字节
    mbuf->tail=mbuf->offset+tot_len;

    // 源地址与目的地址一样那么丢弃该数据包
    if(!memcmp(header->dst_addr,header->src_addr,4)){
        ixc_mbuf_put(mbuf);
        return;
    }

    IXC_MBUF_LOOP_TRACE(mbuf);

    if(IXC_NETIF_WAN==netif->type){
        ixc_ip_handle_from_wan(mbuf,header);
    }else{
        ixc_ip_handle_from_lan(mbuf,header);
    }
}


int ixc_ip_send(struct ixc_mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    int ip_ver= (header->ver_and_ihl & 0xf0) >> 4;

    // 检查IP版本是否符合要求
    if(4!=ip_ver && 6!=ip_ver){
        ixc_mbuf_put(m);
        return -1;
    }

    if(6==ip_ver) return ixc_ip6_send(m);

    m->is_ipv6=0;

    // 丢弃组播或者广播的数据包
    if(header->dst_addr[0]>=224){
        ixc_mbuf_put(m);
        return -1;
    }

    // 如果源地址和目的地址一样那么丢弃该数据包
    if(!memcmp(header->dst_addr,header->src_addr,4)){
        ixc_mbuf_put(m);
        return -1;
    }

    m->netif=NULL;
    ixc_route_handle(m);

    return 0;
}