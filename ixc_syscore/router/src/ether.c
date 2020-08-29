#include<arpa/inet.h>

#include "netif.h"
#include "ether.h"

int ixc_ether_send(struct ixc_mbuf *mbuf,int add_header)
{
    struct ixc_netif *netif=mbuf->netif;

    if(!add_header){
        ixc_netif_send(mbuf);
        return 0;
    }

    return 0;
}

void ixc_ether_handle(struct ixc_mbuf *mbuf)
{
    struct ixc_netif *netif=mbuf->netif;
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

    switch (type){
        // IP
        case 0x800:
            break;
        // ARP
        case 0x806:
            break;
        // IPv6
        case 0x86dd:
            break;
        // pppoe discover
        case 0x8863:
            ixc_mbuf_put(mbuf);
            break;
        /// pppoe session stage
        case 0x8864:
            ixc_mbuf_put(mbuf);
            break;
        default:
            ixc_mbuf_put(mbuf);
            break;
    }
}