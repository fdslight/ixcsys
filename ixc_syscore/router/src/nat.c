#include<string.h>
#include<arpa/inet.h>

#include "nat.h"
#include "pppoe.h"
#include "netif.h"
#include "ether.h"
#include "addr_map.h"
#include "arp.h"
#include "ip.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static int nat_enable=0;
static int nat_is_initialized=0;

struct ixc_nat nat;


/// 获取可用的NAT ID
static struct ixc_nat_id *ixc_nat_id_get(struct ixc_nat_id_set *id_set)
{
    struct ixc_nat_id *id=id_set->head;

    if(NULL!=id){
        id_set->head=id->next;
        id->next=NULL;

        return id;
    }

    if(id_set->cur_id>IXC_NAT_ID_MAX) return NULL;

    id=malloc(sizeof(struct ixc_nat_id));

    if(NULL==id){
        STDERR("no memory for malloc struct ixc_nat_id\r\n");
        return NULL;
    }

    id->id=id_set->cur_id;
    id_set->cur_id+=1;

    return id;
}

/// 释放使用过的NAT ID
static void ixc_nat_id_put(struct ixc_nat_id_set *id_set,struct ixc_nat_id *id)
{
    if(NULL==id) return;

    id->next=id_set->head;
    id_set->head=id;
}


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

static struct ixc_mbuf *ixc_nat_do(struct ixc_mbuf *m,int is_src)
{
    struct netutil_iphdr *iphdr;
    unsigned char addr[4];
    int hdr_len=0;
    unsigned short id=0;
    char key[7],is_found;
    struct ixc_nat_session *session;

    iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    hdr_len=(iphdr->ver_and_ihl & 0x0f)*4;

    if(is_src) memcpy(addr,iphdr->src_addr,4);
    else memcpy(addr,iphdr->dst_addr,4);

    switch(iphdr->protocol){
        case 1:
            break;
        case 7:
            break;
        case 17:
            break;
        case 132:
            break;
        case 136:
            break;
        // 不支持的协议直接丢弃数据包
        default:
            ixc_mbuf_put(m);
            return NULL;
    }

    // 首先检查NAT记录是否存在
    memcpy(key,addr,4);
    key[4]=iphdr->protocol;
    memcpy(key+5,&id,2);

    if(is_src) session=map_find(nat.lan2wan,key,&is_found);
    else session=map_find(nat.wan2lan,key,&is_found);

    // WAN口找不到的那么直接丢弃数据包
    if(NULL==session && !is_src){
        ixc_mbuf_put(m);
        return;
    }

    



    return NULL;
}

static void ixc_nat_lan_send(struct ixc_mbuf *m)
{
    // 未开启NAT那么直接发送数据包
    if(!nat_enable){
        ixc_ip_send(m);
        return;
    }

    m=ixc_nat_do(m,1);
    if(NULL==m) return;
}

int ixc_nat_init(void)
{
    struct map *m;
    int rs;

    bzero(&nat,sizeof(struct ixc_nat));

    nat.icmp_set.cur_id=IXC_NAT_ID_MIN;
    nat.tcp_set.cur_id=IXC_NAT_ID_MIN;
    nat.udp_set.cur_id=IXC_NAT_ID_MIN;
    nat.udplite_set.cur_id=IXC_NAT_ID_MIN;
    nat.sctp_set.cur_id=IXC_NAT_ID_MIN;

    rs=map_new(&m,7);
    if(rs){
        STDERR("cannot init map\r\n");
        return -1;
    }
    nat.lan2wan=m;
    rs=map_new(&m,7);
    if(rs){
        STDERR("cannot init map\r\n");
        return -1;
    }
    nat.wan2lan=m;

    nat_is_initialized=1;
    return 0;
}

void ixc_nat_uninit(void)
{

    nat_is_initialized=0;
    return;
}

void ixc_nat_handle(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;

    if(IXC_NETIF_WAN==netif->type) ixc_nat_wan_send(m);
    else ixc_nat_lan_send(m);

}