
#include<string.h>
#include<time.h>

#include "addr_map.h"
#include "arp.h"
#include "pppoe.h"
#include "ether.h"
#include "debug.h"
#include "pppoe.h"
#include "icmpv6.h"

#include "../../../pywind/clib/sysloop.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_addr_map addr_map;
static int addr_map_is_initialized=0;
static struct sysloop *addr_map_sysloop=NULL;

static void ixc_addr_map_del_cb(void *data)
{
    struct ixc_addr_map_record *r=data;
    struct time_data *tdata=r->tdata;

    if(NULL!=tdata) tdata->is_deleted=1;
    
    free(r);
}

static void ixc_addr_map_sysloop_cb(struct sysloop *lp)
{
    if(!addr_map_is_initialized){
        STDERR("addr map not initialized\r\n");
        return;
    }
    //DBG_FLAGS;
    time_wheel_handle(&(addr_map.time_wheel));
}

static void ixc_addr_map_timeout_cb(void *data)
{
    struct ixc_addr_map_record *r=data;
    struct time_data *tdata=r->tdata;
    time_t now_time=time(NULL);

    //DBG_FLAGS;

    // 超时释放内存
    if(now_time - r->up_time >= IXC_ADDR_MAP_TIMEOUT){
        if(r->is_ipv6) {
            map_del(addr_map.ip6_record,(char *)(r->address),ixc_addr_map_del_cb);
        }else {
            map_del(addr_map.ip_record,(char *)(r->address),ixc_addr_map_del_cb);
            IXC_PRINT_IP("addr map delete",r->address);
        }
        return;
    }

    tdata=time_wheel_add(&(addr_map.time_wheel),r,10);
    r->tdata=tdata;
    //tdata->data=r;

    // 对IPv6的处理方式
    if(r->is_ipv6){
        ixc_icmpv6_send_ns(r->netif,r->netif->ip6addr,r->address);
        return;
    }
    // 发送ARP请求,检查ARP记录
    ixc_arp_send(r->netif,r->hwaddr,r->address,IXC_ARP_OP_REQ);
}

int ixc_addr_map_init(void)
{
    int rs;
    struct map *m;
    bzero(&addr_map,sizeof(struct ixc_addr_map));

    addr_map_sysloop=sysloop_add(ixc_addr_map_sysloop_cb,NULL);

    if(NULL==addr_map_sysloop){
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }

    rs=time_wheel_new(&(addr_map.time_wheel),IXC_ADDR_MAP_TIMEOUT*2/10,10,ixc_addr_map_timeout_cb,256);
    if(rs){
        sysloop_del(addr_map_sysloop);
        STDERR("cannot create time wheel for address map\r\n");
        return -1;
    }

    rs=map_new(&m,4);
    if(rs){
        sysloop_del(addr_map_sysloop);
        time_wheel_release(&(addr_map.time_wheel));
        STDERR("cannot create map for ipv4 address map\r\n");
        return -1;
    }

    addr_map.ip_record=m;
    rs=map_new(&m,16);
    if(rs){
        sysloop_del(addr_map_sysloop);
        map_release(addr_map.ip_record,NULL);
        time_wheel_release(&(addr_map.time_wheel));
        STDERR("cannot create map for ipv6 address map\r\n");
        return -1;
    }

    addr_map.ip6_record=m;
    addr_map_is_initialized=1;

    return 0;
}

void ixc_addr_map_uninit(void)
{
    if(!addr_map_is_initialized) return;

    map_release(addr_map.ip_record,ixc_addr_map_del_cb);
    map_release(addr_map.ip6_record,ixc_addr_map_del_cb);

    time_wheel_release(&(addr_map.time_wheel));
    sysloop_del(addr_map_sysloop);

    addr_map_is_initialized=0;
}

int ixc_addr_map_add(struct ixc_netif *netif,unsigned char *ip,unsigned char *hwaddr,int is_ipv6)
{
    struct time_data *tdata;
    struct ixc_addr_map_record *r;
    struct map *map;
    char is_found;
    int rs;

    if(!addr_map_is_initialized){
        STDERR("addr map not initialized\r\n");
        return -1;
    }

    map=is_ipv6?addr_map.ip6_record:addr_map.ip_record;
    r=map_find(map,(char *)ip,&is_found);
    // 如果找的到记录那么直接返回
    if(NULL!=r) return 0;
    
    r=malloc(sizeof(struct ixc_addr_map_record));
    if(NULL==r){
        STDERR("cannot malloc for struct ixc_addr_map_record\r\n");
        return -1;
    }

    rs=map_add(map,(char *)ip,r);
    if(rs){
        STDERR("map add fail\r\n");
        free(r);
        return -1;
    }

    tdata=time_wheel_add(&(addr_map.time_wheel),r,10);
    if(NULL==tdata){
        STDERR("cannot add to timer\r\n");
        map_del(map,(char *)ip,NULL);
        free(r);
        return -1;
    }

    r->netif=netif;
    r->tdata=tdata;
    tdata->data=r;

    if(is_ipv6) memcpy(r->address,ip,16);
    else memcpy(r->address,ip,4);

    r->is_ipv6=is_ipv6;

    memcpy(r->hwaddr,hwaddr,6);
    r->up_time=time(NULL);

    return 0;
}

struct ixc_addr_map_record *ixc_addr_map_get(unsigned char *ip,int is_ipv6)
{
    struct ixc_addr_map_record *r=NULL;
    struct map *map;
    char is_found;

    map=is_ipv6?addr_map.ip6_record:addr_map.ip_record;
    r=map_find(map,(char *)ip,&is_found);

    return r;
}

static void ixc_addr_map_handle_for_ipv6(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;
    struct ixc_addr_map_record *r=NULL;
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);

    // 如果直通那么直通数据包
    if(m->passthrough){
        ixc_ether_send(m,0);
        return;
    }

    // 如果是WAN口并且不是同网段地址那么直接使用默认网关
    if(netif->type==IXC_NETIF_WAN && !ixc_netif_is_subnet(netif,header->dst_addr,1,0)){
        memcpy(m->src_hwaddr,netif->hwaddr,6);
        memcpy(m->dst_hwaddr,netif->ip6_default_router_hwaddr,6);
        ixc_ether_send(m,1);
        return;
    }
   
    r=ixc_addr_map_get(m->next_host,1);
    // 找到记录那么直接发送
    if(r){
        memcpy(m->dst_hwaddr,r->hwaddr,6);
        r->up_time=time(NULL);
        ixc_ether_send(m,1);
        return;
    }
    // 找不到记录那么就发送NDP RS报文
    ixc_icmpv6_send_ns(netif,netif->ip6_local_link_addr,header->dst_addr);
    ixc_mbuf_put(m);
}

static void ixc_addr_map_handle_for_ip(struct ixc_mbuf *m)
{
    struct ixc_addr_map_record *r=NULL;
    struct ixc_netif *netif=m->netif;

    unsigned char brd[]={
        0xff,0xff,0xff,
        0xff,0xff,0xff
    };

    // 查找网关记录是否存在,如果不存在那么就发送ARP请求
    r=ixc_addr_map_get(m->next_host,0);
    
    if(NULL==r){
        ixc_arp_send(netif,brd,m->next_host,IXC_ARP_OP_REQ);
        ixc_mbuf_put(m);
        return;
    }

    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memcpy(m->dst_hwaddr,r->hwaddr,6);
    r->up_time=time(NULL);

    ixc_ether_send(m,1);
}

void ixc_addr_map_handle(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;

    // 如果目标网卡是WAN并且数据来自于LAN那么直接发送到PPPoE
    if(ixc_pppoe_is_enabled() && netif->type==IXC_NETIF_WAN && m->from==IXC_MBUF_FROM_LAN){
        ixc_pppoe_handle(m);
        return;
    }

    if(m->is_ipv6) ixc_addr_map_handle_for_ipv6(m);
    else ixc_addr_map_handle_for_ip(m);
}