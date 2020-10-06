
#include<string.h>
#include<time.h>

#include "addr_map.h"
#include "arp.h"
#include "pppoe.h"
#include "ether.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/sysloop.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_addr_map addr_map;
static int addr_map_is_initialized=0;
static struct sysloop *addr_map_sysloop=NULL;

static void ixc_addr_map_sysloop_cb(struct sysloop *lp)
{
    if(!addr_map_is_initialized){
        STDERR("addr map not initialized\r\n");
        return;
    }
    time_wheel_handle(&(addr_map.time_wheel));
}

static void ixc_addr_map_timeout_cb(void *data)
{
    struct ixc_addr_map_record *r=data;
    struct time_data *tdata=r->tdata;

    time_t now_time=time(NULL);

    // 超时释放内存
    if(now_time - r->up_time >= IXC_ADDR_MAP_TIMEOUT){
        tdata->is_deleted=1;
        free(r);
        return;
    }

    tdata->is_deleted=1;
    tdata=time_wheel_add(&(addr_map.time_wheel),r,now_time-r->up_time);
    
    r->tdata=tdata;

    // 对IPv6的处理方式
    if(r->is_ipv6){
        return;
    }

    // 发送ARP请求,检查ARP记录
    ixc_arp_send(r->netif,r->hwaddr,r->address,IXC_ARP_OP_REQ);
}

static void ixc_addr_map_del_cb(void *data)
{
    struct ixc_addr_map_record *r=data;
    struct time_data *tdata=r->tdata;

    tdata->is_deleted=1;
    free(r);
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

    tdata=time_wheel_add(&(addr_map.time_wheel),r,IXC_ADDR_MAP_TIMEOUT*0.8);
    if(NULL==tdata){
        STDERR("cannot add to timer\r\n");
        map_del(map,(char *)ip,NULL);
        free(r);
        return -1;
    }

    r->netif=netif;
    r->tdata=tdata;

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
    ixc_mbuf_put(m);
}

static void ixc_addr_map_handle_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_addr_map_record *r=NULL;
    struct ixc_netif *netif=m->netif;

    unsigned char brd[]={
        0xff,0xff,0xff,
        0xff,0xff,0xff
    };

    // 对于同一个网段的处理方式
    if(ixc_netif_is_subnet(netif,iphdr->dst_addr,0,0)){
        r=ixc_addr_map_get(iphdr->dst_addr,0);

        // 找不到地址映射记录那么发送ARP请求数据包,并且丢弃当前数据包
        if(NULL==r){
            ixc_arp_send(netif,brd,iphdr->dst_addr,IXC_ARP_OP_REQ);
            ixc_mbuf_put(m);
            return;
        }
        // 找到记录那么拷贝硬件地址并发送数据包
        memcpy(m->dst_hwaddr,r->hwaddr,6);
        ixc_ether_send(m,1);
        return;
    }

    // 不是同一个网段地址的处理
    // 检查WAN PPPoE是否开启,如果开启直接发送到PPPoE
    if(ixc_pppoe_is_enabled() && IXC_NETIF_WAN==netif->type){
        ixc_pppoe_handle(m);
        return;
    }

    // 查找网关记录是否存在,如果不存在那么就发送ARP请求
    r=ixc_addr_map_get(m->gw,0);
    if(NULL==r){
        ixc_arp_send(netif,brd,m->gw,IXC_ARP_OP_REQ);
        ixc_mbuf_put(m);
        return;
    }

    memcpy(m->dst_hwaddr,r->hwaddr,6);
    DBG_FLAGS;
    ixc_ether_send(m,1);
}

void ixc_addr_map_handle(struct ixc_mbuf *m)
{
    if(m->is_ipv6) ixc_addr_map_handle_for_ipv6(m);
    else ixc_addr_map_handle_for_ip(m);
}