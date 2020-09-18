#include<arpa/inet.h>
#include<string.h>

#include "ip.h"
#include "ip6.h"
#include "netif.h"
#include "route.h"
#include "icmp.h"
#include "addr_map.h"
#include "arp.h"
#include "ether.h"
#include "dhcp_client.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/debug.h"


static void ixc_ip_handle_icmp(struct ixc_mbuf *m,struct netutil_iphdr *header)
{
    struct ixc_netif *netif=m->netif;

    // 不是发送本机的ICMP直接发送到路由
    if(memcmp(netif->ipaddr,header->dst_addr,4)){
        ixc_route_handle(m,0);
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

    // 检查是DHCP报文并且开启DHCP的那么处理DHCP报文
    if(ntohs(udphdr->dst_port)==68 && ntohs(udphdr->src_port)==67 && ixc_dhcp_client_is_enabled()){
        ixc_dhcp_client_handle(m);
        return;
    }

    ixc_mbuf_put(m);

}

static void ixc_ip_handle_from_lan(struct ixc_mbuf *m,struct netutil_iphdr *iphdr)
{
    struct netutil_udphdr *udphdr;
    int hdr_len=(iphdr->ver_and_ihl & 0x0f) *4;

    if(1==iphdr->protocol){
        ixc_ip_handle_icmp(m,iphdr);
        return;
    }

    ixc_mbuf_put(m);
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

    if(IXC_NETIF_WAN==netif->type){
        ixc_ip_handle_from_wan(mbuf,header);
    }else{
        ixc_ip_handle_from_lan(mbuf,header);
    }
}

int ixc_ip_send(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_addr_map_record *r=ixc_addr_map_get(header->dst_addr,0);
    unsigned char dst_hwaddr[]={0xff,0xff,0xff,0xff,0xff,0xff};

    memcpy(m->src_hwaddr,netif->hwaddr,6);

    //STDERR("src:%d.%d.%d.%d\r\n",header->src_addr[0],header->src_addr[1],header->src_addr[2],header->src_addr[3]);
    //STDERR("dst:%d.%d.%d.%d\r\n",header->dst_addr[0],header->dst_addr[1],header->dst_addr[2],header->dst_addr[3]);

    // 找不到地址映射记录就发送ARP请求包并丢弃当前数据包
    if(!r){
        ixc_arp_send(netif,dst_hwaddr,header->dst_addr,IXC_ARP_OP_REQ);
        ixc_mbuf_put(m);
        return 0;
    }

    m->link_proto=0x800;
    memcpy(m->dst_hwaddr,r->hwaddr,6);

    //STDERR("%x:%x:%x:%x:%x:%x\r\n",r->hwaddr[0],r->hwaddr[1],r->hwaddr[2],r->hwaddr[3],r->hwaddr[4],r->hwaddr[5]);
    ixc_ether_send(m,1);

    return 0;
}