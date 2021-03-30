#include<arpa/inet.h>
#include<string.h>

#include "ether.h"
#include "arp.h"
#include "ip.h"
#include "ip6.h"
#include "netif.h"
#include "router.h"
#include "pppoe.h"

#include "../../../pywind/clib/debug.h"

int ixc_ether_send(struct ixc_mbuf *mbuf,int add_header)
{
    struct ixc_ether_header eth_header;
    int size;

    if(!add_header){
        ixc_netif_send(mbuf);
        return 0;
    }

    // 首先屏蔽旧的头部
    mbuf->begin=mbuf->offset;

    memcpy(eth_header.dst_hwaddr,mbuf->dst_hwaddr,6);
    memcpy(eth_header.src_hwaddr,mbuf->src_hwaddr,6);

    eth_header.type=htons(mbuf->link_proto);

    mbuf->begin=mbuf->begin-sizeof(struct ixc_ether_header);

    memcpy(mbuf->data+mbuf->begin,&eth_header,sizeof(struct ixc_ether_header));

    size=mbuf->end-mbuf->begin;

    if(size<0){
        STDERR("size cannot is zero\r\n");
        ixc_mbuf_put(mbuf);
        return -1;
    }

    // 填充以太网以便满足60字节
    if(size<60){
        bzero(mbuf->data+mbuf->end,60-size);
        mbuf->end+=(60-size);
    }
 
    ixc_netif_send(mbuf);

    return 0;
}

void ixc_ether_handle(struct ixc_mbuf *mbuf)
{
    struct ixc_ether_header *header;
    struct ixc_netif *netif=mbuf->netif;
    unsigned short type;
    
    // 检查长度是否合法,不合法直接丢包
    if(mbuf->end-mbuf->begin<14){
        ixc_mbuf_put(mbuf);
        return;
    }

    //IXC_MBUF_LOOP_TRACE(mbuf);

    header=(struct ixc_ether_header *)(mbuf->data+mbuf->begin);
    type=ntohs(header->type);

    // 限定只支持以太网
    if(type<0x200){
        ixc_mbuf_put(mbuf);
        return;
    }
    
    // 此处检查目标MAC地址是否是本地地址，广播和多播排除在外

    memcpy(mbuf->dst_hwaddr,header->dst_hwaddr,6);
    memcpy(mbuf->src_hwaddr,header->src_hwaddr,6);

    mbuf->offset+=14;
    mbuf->link_proto=type;
    
    if(ixc_pppoe_is_enabled() && IXC_NETIF_WAN==netif->type){
        // 如果WAN口开启PPPoE那么限制只支持PPPoE数据包
        if(type!=0x8864 && type!=0x8863){
            ixc_mbuf_put(mbuf);
            return;
        }
    }

    switch (type){
        // IP
        case 0x0800:
            ixc_ip_handle(mbuf);
            break;
        // ARP
        case 0x0806:
            ixc_arp_handle(mbuf);
            break;
        // IPv6
        case 0x86dd:
            ixc_ip6_handle(mbuf);
            break;
        // PPPoE discovery
        case 0x8863:
            if(IXC_NETIF_LAN==netif->type) ixc_mbuf_put(mbuf);
            else ixc_pppoe_handle(mbuf);
            break;
        // PPPoE session
        case 0x8864:
            if(IXC_NETIF_LAN==netif->type) ixc_mbuf_put(mbuf);
            else ixc_pppoe_handle(mbuf);
            break;
        default:
            ixc_mbuf_put(mbuf);
            break;
    }
}

int ixc_ether_send2(struct ixc_mbuf *m)
{
    struct ixc_ether_header *header;
    int size=0;

    if(NULL==m) return 0;
    
    if(NULL==m->netif){
        STDERR("empty netif\r\n");
        ixc_mbuf_put(m);
        return -1;
    }

    header=(struct ixc_ether_header *)(m->data+m->begin);
    m->link_proto=ntohs(header->type);

    size=m->end-m->begin;

    // 检查数据包是否合法
    if(size<13){
        ixc_mbuf_put(m);
        return -1;
    }

    if(ntohs(header->type)<0x0101){
        ixc_mbuf_put(m);
        return -1;
    }

    if(size<60){
        bzero(m->data+m->end,60-size);
        m->end+=(60-size);
    }

    ixc_netif_send(m);

    return 0;
}

int ixc_ether_get_multi_hwaddr_by_ip(unsigned char *ip,unsigned char *result)
{
    result[0]=0x01;
    result[1]=0x00;
    result[2]=0x5e;
    result[3]=ip[1] & 0x7f;
    result[4]=ip[2];
    result[5]=ip[3];

    return 0;
}

int ixc_ether_get_multi_hwaddr_by_ipv6(unsigned char *ip6,unsigned char *result)
{
    result[0]=0x33;
    result[1]=0x33;

    memcpy(&result[2],ip6+12,4);

    return 0;
}

int ixc_ether_is_self(struct ixc_netif *netif,unsigned char *hwaddr)
{
    // 检查是否是多播地址
    if(hwaddr[0] & 0x01 == 1) return 1;
    if(!memcmp(hwaddr,netif->hwaddr,6)) return 1;
    
    return 0;
}
