#include<string.h>
#include<stdlib.h>

#include "route.h"
#include "router.h"
#include "udp_src_filter.h"
#include "local.h"
#include "addr_map.h"
#include "arp.h"
#include "qos.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/debug.h"
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

int ixc_route_add(unsigned char *subnet,unsigned char prefix,int is_ipv6,int is_linked)
{
    struct ixc_route_info *r;
    char key[17],is_found;
    struct map *m=is_ipv6?route.ip6_rt:route.ip_rt;
    int rs;

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
    r->is_linked=is_linked;
    r->is_ipv6=is_ipv6;

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
    // 存在的话直接返回
    if(r) return;
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
        subnet_calc_with_msk(ip,p->mask,is_ipv6,(unsigned char *)key);
        key[idx]=p->prefix;
        r=map_find(m,key,&is_found);
        if(r) break;
    }

    return r;
}


static void ixc_route_handle_for_ipv6(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);
    //struct ixc_route_info *r=ixc_route_match(header->dst_addr,1);
    //struct ixc_netif *netif=m->netif;

    // 检查地址是否可以被转发
    if(header->dst_addr[0]==0 || ((header->dst_addr[0]) & 0xf0)==0xf0){
        ixc_mbuf_put(m);
        return;
    }
    
    ixc_mbuf_put(m);
}

static void ixc_route_handle_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_route_info *r;
    struct ixc_netif *netif;
    struct ixc_addr_map_record *addr_map_r;
    unsigned char link_brd[]={
        0xff,0xff,0xff,
        0xff,0xff,0xff
    };

    unsigned char *local_addr=ixc_local_get(0,0);
    unsigned short csum;

    // 组播数据包不能经过路由器,因此丢弃组播数据包
    if(iphdr->dst_addr[0] >=224 && iphdr->dst_addr[0]<=239){
        ixc_mbuf_put(m);
        return;
    }

    // 如果目标地址是本地地址,那么发送到本地机器
    if(!memcmp(local_addr,iphdr->dst_addr,4)){
        ixc_local_send(m);
        return;
    }

    // 如果是本地网络的地址,那么发送到本地网络
    netif=ixc_netif_get(IXC_NETIF_LAN);
    if(ixc_netif_is_subnet(netif,iphdr->dst_addr,0,0)){
        m->netif=netif;
        addr_map_r=ixc_addr_map_get(iphdr->dst_addr,0);

        // 如果找到本地网络的地址映射记录,那么发送到本地网络
        if(NULL!=addr_map_r){
            memcpy(m->src_hwaddr,netif->hwaddr,6);
            memcpy(m->dst_hwaddr,addr_map_r->hwaddr,6);
            m->link_proto=0x0800;

            // 加入到QOS
            ixc_qos_add(m);
            return;
        }
        // 找不到数据包那么就发送ARP请求并丢弃当前数据包
        ixc_arp_send(netif,link_brd,iphdr->dst_addr,IXC_ARP_OP_REQ);
        ixc_mbuf_put(m);
        return;
    }

    // 如果ttl为1那么发送ICMP报文告知
    if(iphdr->ttl<1){
        ixc_mbuf_put(m);
        return;
    }

    r=ixc_route_match(iphdr->dst_addr,0);
    // 减少头部ttl的数值
    csum=csum_calc_incre(iphdr->ttl,iphdr->ttl-1,iphdr->checksum);
    iphdr->checksum=csum;

    // 找不到匹配匹配路由直接发送到udp src filter
    if(!r){
        ixc_udp_src_filter_handle(m);
        return;
    }
    
    if(r->is_linked) ixc_router_send(netif->type,0,0,m->data+m->begin,m->end-m->begin);
    else ixc_router_send(netif->type,iphdr->protocol,0,m->data+m->offset,m->tail-m->offset);
}

void ixc_route_handle(struct ixc_mbuf *m)
{
    if(m->is_ipv6) ixc_route_handle_for_ipv6(m);
    else ixc_route_handle_for_ip(m);
}