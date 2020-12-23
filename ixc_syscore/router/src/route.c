#include<string.h>
#include<stdlib.h>

#include "route.h"
#include "router.h"
#include "src_filter.h"
#include "arp.h"
#include "qos.h"
#include "debug.h"
#include "ip6.h"
#include "ip.h"
#include "icmpv6.h"
#include "icmp.h"
#include "addr_map.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_route route;
static int route_is_initialized=0;

static int ixc_route_prefix_add(unsigned char prefix,int is_ipv6)
{
    struct ixc_route_prefix *p=NULL,*t,**head;

    if(is_ipv6){
        t=route.ip6_pre_head;
        head=&(route.ip6_pre_head);
    }else{
        t=route.ip_pre_head;
        head=&(route.ip_pre_head);
    }

    while(NULL!=t){
        if(t->prefix==prefix){
            p=t;
            break;
        }
        t=t->next;
    }

    // 已经存在那么引用计数加1
    if(p){
        p->refcnt+=1;
        return 0;
    }

    t=malloc(sizeof(struct ixc_route_prefix));

    if(NULL==t){
        STDERR("cannot malloc for struct ixc_route_prefix\r\n");
        return -1;
    }

    t->next=NULL;
    t->refcnt=1;
    t->prefix=prefix;
    
    msk_calc(prefix,is_ipv6,t->mask);
    
    if(NULL==*head){
        *head=t;
        return 0;
    }

    p=t;
    t=*head;

    // 首先检查是否比第一个大
    if(prefix>t->prefix){
        p->next=t;
        *head=p;
        return 0;
    }

    while(NULL!=t){
        if(prefix < t->prefix){
            p->next=t->next;
            t->next=p;
            break;
        }
        t=t->next;
    }

    return 0;
}

static void ixc_route_prefix_del(unsigned char prefix,int is_ipv6)
{
    struct ixc_route_prefix *p=NULL,*t,**head;

    if(is_ipv6){
        t=route.ip6_pre_head;
        head=&(route.ip6_pre_head);
    }else{
        t=route.ip_pre_head;
        head=&(route.ip_pre_head);
    }

    while(NULL!=t){
        if(t->prefix==prefix){
            p=t;
            break;
        }
        t=t->next;
    }

    // 不存在直接返回
    if(!p) return;

    // 减少引用计数
    p->refcnt-=1;
    // 如果引用计数不为0那么直接返回
    if(0!=p->refcnt) return;

    // 当为head节点的处理方式
    if(prefix==(*head)->prefix){
        *head=p->next;
        free(p);
        return;
    }

    t=*head;
    p=t->next;

    while(NULL!=p){
        if(p->prefix==prefix){
            t->next=p->next;
            free(p);
            break;
        }
        t=p;
        p=p->next;
    }

}

static void ixc_route_del_cb(void *data)
{
    struct ixc_route_info *r=data;

    ixc_route_prefix_del(r->prefix,r->is_ipv6);
    free(data);
}


int ixc_route_init(void)
{
    struct map *m;
    int rs;

    bzero(&route,sizeof(struct ixc_route));

    rs=map_new(&m,5);
    if(rs){
        STDERR("ceate ipv4 map failed\r\n");
        return -1;
    }
    route.ip_rt=m;
    
    rs=map_new(&m,17);
    if(rs){
        map_release(route.ip_rt,NULL);
        STDERR("create ipv6 map failed\r\n");
        return -1;
    }
    route.ip6_rt=m;

    return 0;
}

void ixc_route_uninit(void)
{
    map_release(route.ip_rt,ixc_route_del_cb);
    map_release(route.ip6_rt,ixc_route_del_cb);

    route_is_initialized=0;
}

int ixc_route_add(unsigned char *subnet,unsigned char prefix,unsigned char *gw,int is_ipv6)
{
    struct ixc_route_info *r;
    char key[17],is_found;
    struct map *m=is_ipv6?route.ip6_rt:route.ip_rt;
    int rs,is_default;
    unsigned char default_route[]={
        0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00
    };
    struct ixc_netif *netif=NULL;

    if(is_ipv6){
        if(!memcmp(default_route,subnet,16) && 0==prefix) is_default=1;
        else is_default=0;
    }else{
        if(!memcmp(default_route,subnet,4) && 0==prefix) is_default=1;
        else is_default=0;
    }

    if(is_default) netif=ixc_netif_get(IXC_NETIF_WAN);
    else netif=ixc_netif_get_with_subnet_ip(gw,is_ipv6);

    if(NULL!=gw && NULL==netif){
        STDERR("not found netif for add route\r\n");
        return -1;
    }
    
    if(is_ipv6){
        memcpy(key,subnet,16);
        key[16]=prefix;
    }else{
        memcpy(key,subnet,4);
        key[4]=prefix;
    }

    r=map_find(m,key,&is_found);
    // 存在的话直接返回
    if(r) return 0;
    
    r=malloc(sizeof(struct ixc_route_info));
    if(NULL==r){
        STDERR("no memory for malloc\r\n");
        return -1;
    }

    bzero(r,sizeof(struct ixc_route_info));

    rs=ixc_route_prefix_add(prefix,is_ipv6);
    if(rs){
        free(r);
        STDERR("add prefix failed\r\n");
        return -1;
    }

    rs=map_add(m,key,r);
    if(rs){
        free(r);
        ixc_route_prefix_del(prefix,is_ipv6);
        STDERR("add to route table failed\r\n");
        return -1;
    }

    if(is_ipv6) memcpy(r->subnet,subnet,16);
    else memcpy(r->subnet,subnet,4);
    
    r->prefix=prefix;
    r->is_ipv6=is_ipv6;
    r->netif=netif;

    if(NULL==netif){
        DBG("route forward to application\r\n");
    }

    if(NULL!=gw){
        if(is_ipv6) memcpy(r->gw,gw,16);
        else memcpy(r->gw,gw,4);
    }

    return 0;
}

void ixc_route_del(unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    struct ixc_route_info *r;
    char key[17],is_found;
    struct map *m=is_ipv6?route.ip6_rt:route.ip_rt;

    if(is_ipv6){
        memcpy(key,subnet,16);
        key[16]=prefix;
    }else{
        memcpy(key,subnet,4);
        key[4]=prefix;
    }

    r=map_find(m,key,&is_found);
    // 如果不存在的话直接返回
    if(!r) return;
    map_del(m,key,ixc_route_del_cb);
}

struct ixc_route_info *ixc_route_match(unsigned char *ip,int is_ipv6)
{
    struct ixc_route_prefix *p=is_ipv6?route.ip6_pre_head:route.ip_pre_head;
    char key[17];
    struct ixc_route_info *r=NULL;
    int idx=is_ipv6?16:4;
    struct map *m=is_ipv6?route.ip6_rt:route.ip_rt;
    char is_found;

    while(NULL!=p){
        //DBG_FLAGS;
        subnet_calc_with_msk(ip,p->mask,is_ipv6,(unsigned char *)key);
        key[idx]=p->prefix;
        r=map_find(m,key,&is_found);
        if(r) break;
        p=p->next;
    }

    return r;
}

struct ixc_route_info *ixc_route_get(unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    struct ixc_route_info *r_info;
    char key[17];
    int size=is_ipv6?16:4;
    struct map *m=is_ipv6?route.ip6_rt:route.ip_rt;
    char is_found;

    memcpy(key,subnet,size);
    key[size]=prefix;

    r_info=map_find(m,key,&is_found);

    return r_info;
}

static void ixc_route_handle_for_ipv6_local(struct ixc_mbuf *m,struct netutil_ip6hdr *header)
{
    // 只支持ICMPv6协议
    if(header->next_header!=58){
        ixc_mbuf_put(m);
        return;
    }

    ixc_icmpv6_handle(m,header);
}

static void ixc_route_handle_for_ipv6(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_route_info *r=ixc_route_match(header->dst_addr,1);
    struct ixc_netif *netif=m->netif;

    // 检查地址是否可以被转发
    if(header->dst_addr[0]==0xff){
        ixc_route_handle_for_ipv6_local(m,header);
        return;
    }

    if(header->dst_addr[0]==0xfe && (header->dst_addr[1] & 0xc0)==0x80){
        ixc_route_handle_for_ipv6_local(m,header);
        return;
    }

    // 检查IP地址是否指向自己
    if(!memcmp(header->dst_addr,netif->ip6addr,16)){
        ixc_route_handle_for_ipv6_local(m,header);
        return;
    }

    if(NULL==r){
        ixc_mbuf_put(m);
        return;
    }

    // 如果没有网卡,那么发送到其他应用
    if(NULL==r->netif){
        if(route.is_linked) ixc_router_send(netif->type,0,0,m->data+m->begin,m->end-m->begin);
        else ixc_router_send(netif->type,header->next_header,0,m->data+m->offset,m->tail-m->offset);

        // 这里丢弃数据包,避免内存泄漏
        ixc_mbuf_put(m);
        return;
    }

    netif=r->netif;
    m->netif=netif;
    m->link_proto=0x86dd;

    memcpy(m->src_hwaddr,netif->hwaddr,6);

    // 如果是本地网段,把next host指向下一台主机
    if(ixc_netif_is_subnet(netif,header->dst_addr,1,0)){
        memcpy(m->next_host,header->dst_addr,16);
    }else{
        memcpy(m->next_host,r->gw,16);
    }
    
    if(m->from==IXC_MBUF_FROM_LAN){
        ixc_src_filter_handle(m);
    }else{
        ixc_qos_add(m);
    }
}

static void ixc_route_handle_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_route_info *r;
    struct ixc_netif *netif=m->netif;
    unsigned short ttl;

    unsigned short csum;

    // 保留地址直接丢弃
    if(iphdr->dst_addr[0]>=224){
        ixc_mbuf_put(m);
        return;
    }

    // 链路本地地址丢弃数据包
    if(iphdr->dst_addr[0]==169 && iphdr->dst_addr[1]==254){
        ixc_mbuf_put(m);
        return;
    }

    r=ixc_route_match(iphdr->dst_addr,0);

    // 如果找不到理由,那么就丢弃数据包
    if(NULL==r){
        IXC_PRINT_IP("route not found for dest ip",iphdr->dst_addr);
        ixc_mbuf_put(m);
        return;
    }

    //IXC_PRINT_IP("route found for dest ip",iphdr->dst_addr);

    // 如果ttl为1那么发送ICMP报文告知
    if(iphdr->ttl<=1){
        ixc_mbuf_put(m);
        return;
    }

    // 如果是本机地址的处理
    if(!memcmp(iphdr->dst_addr,netif->ipaddr,4)){
        // 本机只处理ICMP协议
        if(iphdr->protocol!=1){
            ixc_mbuf_put(m);
            return;
        }
        ixc_icmp_handle_self(m);
        return;
    }

    // 如果没有网卡,那么发送到其他应用
    if(NULL==r->netif){
        DBG("forward data to application\r\n");
        if(route.is_linked) ixc_router_send(netif->type,0,IXC_FLAG_ROUTE_FWD,m->data+m->begin,m->end-m->begin);
        else ixc_router_send(netif->type,iphdr->protocol,IXC_FLAG_ROUTE_FWD,m->data+m->offset,m->tail-m->offset);

        // 这里丢弃数据包,避免内存泄漏
        ixc_mbuf_put(m);
        return;
    }

    m->netif=r->netif;
    netif=m->netif;

    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memcpy(m->next_host,r->gw,4);

    ttl=iphdr->ttl;
    // 减少头部ttl的数值
    csum=csum_calc_incre(ttl,ttl-1,iphdr->checksum);
    iphdr->checksum=csum;
    iphdr->ttl-=1;
    m->link_proto=0x0800;

    if(ixc_netif_is_subnet(netif,iphdr->dst_addr,0,0)){
        memcpy(m->next_host,iphdr->dst_addr,4);
    }else{
        memcpy(m->next_host,r->gw,4);
    }

    // 如果是LAN节点那么经过UDP source,否则的直接通过qos出去
    if(m->from==IXC_MBUF_FROM_LAN){
        ixc_src_filter_handle(m);
    }else{
        ixc_addr_map_handle(m);
    }
}

void ixc_route_handle(struct ixc_mbuf *m)
{
    IXC_MBUF_LOOP_TRACE(m);
    
    if(m->is_ipv6) ixc_route_handle_for_ipv6(m);
    else ixc_route_handle_for_ip(m);
}

int ixc_route_set_is_linkpkt_for_app(int is_linked)
{
    route.is_linked=is_linked;
    return 0;
}