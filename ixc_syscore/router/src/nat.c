#include<string.h>
#include<arpa/inet.h>

#include "nat.h"
#include "pppoe.h"
#include "netif.h"
#include "ether.h"
#include "addr_map.h"
#include "arp.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static int nat_enable=0;

static void ixc_nat_wan_send(struct ixc_mbuf *m)
{   
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_addr_map_record *r;
    unsigned char dst_hwaddr[6]={0xff,0xff,0xff,0xff,0xff,0xff};

    r=ixc_addr_map_get(header->dst_addr,0);

    // 找不到地址记录那么现在发送ARP请求包并且丢弃数据包
    if(!r){
        ixc_arp_send(m->netif,dst_hwaddr,header->dst_addr,IXC_ARP_OP_REQ);
        ixc_mbuf_put(m);
        return;
    }

    memcpy(m->src_hwaddr,m->netif->hwaddr,6);
    memcpy(m->dst_hwaddr,r->hwaddr,6);

    m->link_proto=htons(0x800);

    // WAN口开启PPPOE那么直接发送PPPOE报文
    if(ixc_pppoe_enable()){
        ixc_pppoe_send(m);
        return;
    }

    // 不是PPPOE直接发送以太网报文
    ixc_ether_send(m,1);
}

static void ixc_nat_lan_send(struct ixc_mbuf *m)
{

}

int ixc_nat_init(void)
{
    return 0;
}

void ixc_nat_uninit(void)
{
    return;
}

void ixc_nat_handle(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;

    if(IXC_NETIF_WAN==netif->type) ixc_nat_wan_send(m);
    else ixc_nat_lan_send(m);

}