#include<arpa/inet.h>
#include<string.h>

#include "arp.h"
#include "netif.h"
#include "ether.h"

static void ixc_arp_handle_request(struct ixc_mbuf *mbuf,struct ixc_arp *arp)
{
    struct ixc_netif *netif=mbuf->netif;
    unsigned char tmp[32];

    // 检查是否是本机的IP地址,不是的话那么就丢弃ARP数据包
    if(memcmp(arp->dst_ipaddr,netif->ipaddr,4)){
        ixc_mbuf_put(mbuf);
        return;
    }
    
    memcpy(mbuf->src_hwaddr,netif->hwaddr,6);
    memcpy(mbuf->dst_hwaddr,arp->src_hwaddr,6);

    memcpy(tmp,arp->src_ipaddr,4);
    memcpy(arp->src_ipaddr,netif->ipaddr,4);

    memcpy(arp->dst_ipaddr,tmp,4);

    memcpy(arp->src_hwaddr,mbuf->src_hwaddr,6);
    memcpy(arp->dst_hwaddr,mbuf->dst_hwaddr,6);

    arp->op=htons(IXC_ARP_OP_RESP);
   
    ixc_ether_send(mbuf,1);
}

static void ixc_arp_handle_response(struct ixc_mbuf *mbuf,struct ixc_arp *arp)
{
    struct ixc_netif *netif=mbuf->netif;

    // 响应非本网卡丢弃数据包
    if(memcmp(arp->dst_ipaddr,netif->ipaddr,4)){
        ixc_mbuf_put(mbuf);
        return;
    }

    // 处理本机器与其他机器IP地址冲突的情况
    if(!memcmp(arp->src_ipaddr,arp->dst_ipaddr,4)){
        ixc_mbuf_put(mbuf);
        return;
    }

    // 添加到地址映射表
    
}

int ixc_arp_send(unsigned char *dst_hwaddr,unsigned char *dst_ipaddr,unsigned short op)
{
    struct ixc_arp arp;
    struct ixc_netif *netif=ixc_netif_get();
    struct ixc_mbuf *m;

    arp.hwaddr_len=6;
    arp.protoaddr_len=4;
    arp.op=htons(op);

    memcpy(arp.src_hwaddr,netif->hwaddr,6);
    memcpy(arp.src_ipaddr,netif->ipaddr,4);

    memcpy(arp.dst_hwaddr,dst_hwaddr,6);
    memcpy(arp.dst_ipaddr,dst_ipaddr,4);

    m=ixc_mbuf_get();

    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return -1;
    }

    m->netif=netif;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=m->begin;
    m->tail=sizeof(struct ixc_arp);
    m->end=m->tail;
    m->link_proto=0x806;

    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memcpy(m->dst_hwaddr,dst_hwaddr,6);
    
    ixc_ether_send(m,1);

    return 0;
}


void ixc_arp_handle(struct ixc_mbuf *mbuf)
{
    struct ixc_arp *arp=(struct ixc_arp *)(mbuf->data+mbuf->begin);
    unsigned short op=ntohs(arp->op);

    // 检查ARP数据包的源MAC地址合法性
    if(memcmp(mbuf->src_hwaddr,arp->src_hwaddr,6)){
        ixc_mbuf_put(mbuf);
        return;
    }

    switch(op){
        case IXC_ARP_OP_REQ:
            ixc_arp_handle_request(mbuf,arp);
            break;
        case IXC_ARP_OP_RESP:
            ixc_arp_handle_response(mbuf,arp);
            break;
        default:
            ixc_mbuf_put(mbuf);
            break;
    }
}