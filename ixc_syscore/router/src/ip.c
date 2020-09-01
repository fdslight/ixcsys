#include<arpa/inet.h>
#include<string.h>

#include "ip.h"
#include "ip6.h"
#include "netif.h"
#include "route.h"
#include "icmp.h"

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


void ixc_ip_handle(struct ixc_mbuf *mbuf)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(mbuf->data+mbuf->offset);
    int version=(header->ver_and_ihl & 0xf0) >> 4;
    unsigned short tot_len;

    if(4!=version){
        ixc_mbuf_put(mbuf);
        return;
    }

    // 首先检查IP长度是否合法
    tot_len=ntohs(header->tot_len);

    if(tot_len > mbuf->tail- mbuf->offset){
        ixc_mbuf_put(mbuf);
        return;
    }

    mbuf->is_ipv6=0;
    
    // 除去以太网的填充字节
    mbuf->tail=mbuf->offset+tot_len;

    switch(header->protocol){
        case 1:
            ixc_ip_handle_icmp(mbuf,header);
            break;
        default:
            ixc_route_handle(mbuf,0);
            break;
    }
}