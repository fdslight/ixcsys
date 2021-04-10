#include<arpa/inet.h>
#include<string.h>
#include<time.h>

#include "arp.h"
#include "netif.h"
#include "ether.h"
#include "addr_map.h"
#include "router.h"
#include "debug.h"
#include "npfwd.h"

static void ixc_arp_handle_request(struct ixc_mbuf *mbuf,struct ixc_arp *arp)
{
    struct ixc_netif *netif=mbuf->netif;
    //unsigned char brd[]={0xff,0xff,0xff,0xff,0xff,0xff};
    
    // 检查是否是本机的IP地址,不是本机的IP地址那么丢弃ARP请求
    if(memcmp(arp->dst_ipaddr,netif->ipaddr,4)){
        ixc_mbuf_put(mbuf);
        return;
    }

    IXC_PRINT_IP("arp request from",arp->src_ipaddr);

    memcpy(mbuf->dst_hwaddr,mbuf->src_hwaddr,6);
    //memcpy(mbuf->dst_hwaddr,brd,6);
    memcpy(mbuf->src_hwaddr,netif->hwaddr,6);

    memcpy(arp->dst_ipaddr,arp->src_ipaddr,4);
    memcpy(arp->src_ipaddr,netif->ipaddr,4);

    memcpy(arp->dst_hwaddr,arp->src_hwaddr,6);
    memcpy(arp->src_hwaddr,netif->hwaddr,6);
    
    arp->op=htons(IXC_ARP_OP_RESP);
   
    ixc_ether_send(mbuf,1);
}

static void ixc_arp_handle_response(struct ixc_mbuf *mbuf,struct ixc_arp *arp)
{
    struct ixc_netif *netif=mbuf->netif;
    struct ixc_addr_map_record *r;


    // 拷贝到DHCP CLIENT与DHCP SERVER
    ixc_npfwd_send_raw(ixc_mbuf_clone(mbuf),0,IXC_FLAG_DHCP_CLIENT);
    ixc_npfwd_send_raw(ixc_mbuf_clone(mbuf),0,IXC_FLAG_DHCP_SERVER);
    

    // 不是本机的IP地址那么丢弃数据包
    if(memcmp(arp->dst_ipaddr,netif->ipaddr,4)){
        ixc_mbuf_put(mbuf);
        return;
    }

    // 不是本机的MAC地址那么丢弃数据包
    if(memcmp(arp->dst_hwaddr,netif->hwaddr,6)){
        ixc_mbuf_put(mbuf);
        return;
    }

    // 处理本机器与其他机器IP地址冲突的情况
    if(!memcmp(arp->src_ipaddr,arp->dst_ipaddr,4)){
        ixc_mbuf_put(mbuf);
        return;
    }

    r=ixc_addr_map_get(arp->src_ipaddr,0);
    
    // 如果不存在那么添加到映射表
    if(NULL==r){
        ixc_addr_map_add(netif,arp->src_ipaddr,arp->src_hwaddr,0);
        ixc_mbuf_put(mbuf);
        return;
    }

    memcpy(r->hwaddr,arp->src_hwaddr,6);
    r->up_time=time(NULL);
}

int ixc_arp_send(struct ixc_netif *netif,unsigned char *dst_hwaddr,unsigned char *dst_ipaddr,unsigned short op)
{
    struct ixc_arp arp;
    struct ixc_mbuf *m;
    unsigned char no_hwaddr[6]={0x00,0x00,0x00,0x00,0x00,0x00};

    arp.htype=htons(1);
    arp.proto_type=htons(0x800);
    arp.hwaddr_len=6;
    arp.protoaddr_len=4;
    arp.op=htons(op);

    memcpy(arp.src_hwaddr,netif->hwaddr,6);
    memcpy(arp.src_ipaddr,netif->ipaddr,4);

    memcpy(arp.dst_hwaddr,no_hwaddr,6);
    memcpy(arp.dst_ipaddr,dst_ipaddr,4);

    m=ixc_mbuf_get();

    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return -1;
    }

    m->netif=netif;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=m->begin;
    m->tail=m->begin+sizeof(struct ixc_arp);
    m->end=m->tail;
    m->link_proto=0x806;

    memcpy(m->data+m->begin,&arp,sizeof(struct ixc_arp));

    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memcpy(m->dst_hwaddr,dst_hwaddr,6);
    
    ixc_ether_send(m,1);

    return 0;
}


void ixc_arp_handle(struct ixc_mbuf *mbuf)
{
    struct ixc_arp *arp=(struct ixc_arp *)(mbuf->data+mbuf->offset);
    unsigned short op=ntohs(arp->op);

    if(ntohs(arp->htype)!=1){
        ixc_mbuf_put(mbuf);
        return;
    }

    if(ntohs(arp->proto_type)!=0x800){
        ixc_mbuf_put(mbuf);
        return;
    }

    //STDERR("%d.%d.%d.%d\r\n",arp->src_ipaddr[0],arp->src_ipaddr[1],arp->src_ipaddr[2],arp->src_ipaddr[3]);
    // 检查ARP数据包的源MAC地址合法性
    if(memcmp(mbuf->src_hwaddr,arp->src_hwaddr,6)){
        ixc_mbuf_put(mbuf);
        return;
    }

    //STDERR("hello,world\r\n");

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