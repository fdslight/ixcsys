#include<arpa/inet.h>
#include<string.h>

#include "ether.h"
#include "arp.h"
#include "ip.h"
#include "ip6.h"

int ixc_ether_send(struct ixc_mbuf *mbuf,int add_header)
{
    struct ixc_ether_header eth_header;
    int size;

    if(!add_header){
        ixc_netif_send(mbuf);
        return 0;
    }

    memcpy(eth_header.dst_hwaddr,mbuf->dst_hwaddr,6);
    memcpy(eth_header.src_hwaddr,mbuf->src_hwaddr,6);

    eth_header.type=htons(mbuf->link_proto);

    mbuf->begin=mbuf->begin-sizeof(struct ixc_ether_header);

    memcpy(mbuf->data+mbuf->begin,&eth_header,sizeof(struct ixc_ether_header));

    size=mbuf->end-mbuf->begin;
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
    unsigned short type;

    // 检查长度是否合法,不合法直接丢包
    if(mbuf->end-mbuf->begin<60){
        ixc_mbuf_put(mbuf);
        return;
    }

    header=(struct ixc_ether_header *)(mbuf->data+mbuf->begin);
    type=ntohs(header->type);

    // 限定只支持以太网
    if(type<0x200){
        ixc_mbuf_put(mbuf);
        return;
    }

    memcpy(mbuf->dst_hwaddr,header->dst_hwaddr,6);
    memcpy(mbuf->src_hwaddr,header->src_hwaddr,6);

    mbuf->offset+=14;
    mbuf->link_proto=type;

    switch (type){
        // IP
        case 0x800:
            ixc_ip_handle(mbuf);
            break;
        // ARP
        case 0x806:
            ixc_arp_handle(mbuf);
            break;
        // IPv6
        case 0x86dd:
            ixc_ip6_handle(mbuf);
            break;
        default:
            ixc_mbuf_put(mbuf);
            break;
    }
}