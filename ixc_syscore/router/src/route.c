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
#include "ip6sec.h"
#include "npfwd.h"
#include "global.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"

static struct ixc_route route;
static int route_is_initialized=0;
static struct time_wheel route_cache_tw;
static struct sysloop *route_sysloop=NULL;

static void route_tcp_mss_modify(struct netutil_tcphdr *tcp_header,int is_ipv6)
{
    unsigned short csum=ntohs(tcp_header->csum);
    unsigned char *ptr=(unsigned char *)tcp_header;
    unsigned short header_len_and_flag=ntohs(tcp_header->header_len_and_flag);
    int header_size=((header_len_and_flag & 0xf000) >> 12) * 4;
    int is_syn= (header_len_and_flag & 0x0002) >> 1;
    unsigned short tcp_mss=0,set_tcp_mss;
    unsigned char *tcp_opt=ptr+20;
    unsigned short *tcp_mss_ptr=NULL;
    unsigned char x,length;

    // 检查是否是SYN报文
    //DBG_FLAGS;
    if(!is_syn) return;
    //DBG_FLAGS;
    if(header_size<=20) return;

    //DBG_FLAGS;
    for(int n=0;n<header_size-20;){
        x=*tcp_opt++;
        if(0==x) break;
        if(1==x) {
            n+=1;
            continue;
        }
        length=*tcp_opt++;
        if(2==x){
            if(4==length) {
                tcp_mss_ptr=(unsigned short *)(tcp_opt);
                memcpy(&tcp_mss,tcp_opt,2);
            }
            break;
       } 
       tcp_opt=tcp_opt+length-2;
       n+=length;
    }

    if(0==tcp_mss) return;
  
    tcp_mss=ntohs(tcp_mss);
    //DBG("tcp mss %d set tcp mss %d\r\n",tcp_mss,set_tcp_mss);

    if(is_ipv6)set_tcp_mss=route.ip6_tcp_mss;
    else set_tcp_mss=route.ip_tcp_mss;

    // 实际TCP MSS小于设置值,那么不修改
    if(tcp_mss<=set_tcp_mss) return;
    //DBG_FLAGS;
    *tcp_mss_ptr=htons(set_tcp_mss);
    csum=csum_calc_incre(tcp_mss,set_tcp_mss,csum);
    tcp_header->csum=htons(csum);

}

static void route_modify_ip_tcp_mss(struct netutil_iphdr *header)
{
    int header_size= (header->ver_and_ihl & 0x0f) * 4;
    unsigned char *ptr=(unsigned char *)header;
    struct netutil_tcphdr *tcp_header=NULL;
    
    // 如果值为0那么不修改tcp mss
    if(0==route.ip_tcp_mss) return;
    if(6!=header->protocol) return;

    ptr=ptr+header_size;

    tcp_header=(struct netutil_tcphdr *)ptr;
    route_tcp_mss_modify(tcp_header,0);
}

static void route_modify_ip6_tcp_mss(struct netutil_ip6hdr *header)
{
    unsigned char *ptr=(unsigned char *)header;
    struct netutil_tcphdr *tcp_header=NULL;

    // 如果值为0那么不修改tcp mss
    if(0==route.ip6_tcp_mss) return;
    if(6!=header->next_header) return;

    ptr=ptr+40;
    tcp_header=(struct netutil_tcphdr *)ptr;
    route_tcp_mss_modify(tcp_header,1);
}


static int ixc_route_prefix_add(unsigned char prefix,int is_ipv6)
{
    struct ixc_route_prefix *p=NULL,*t,**head,*old;

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
        //DBG("add prefix %d\r\n",(*head)->prefix);
        return 0;
    }

    p=t;
    t=*head;
    old=t;

    // 首先检查是否比第一个大
    if(prefix>t->prefix){
        p->next=t;
        *head=p;
        return 0;
    }

    while(NULL!=t){
        if(prefix < t->prefix){
            old=t;
        }
        t=t->next;
    }

    p->next=old->next;
    old->next=p;

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
    // 没有缓存引用直接删除路由
    if(!r->cached_refcnt) free(data);
    // 有缓存那么设置路由无效
    else r->is_invalid=1;
}

static void ixc_route_cache_del_cb(void *data)
{
	struct ixc_route_cache *cache=data;
	struct ixc_route_info *r_info=cache->r_info;

    // 路由无效并且缓存计数为0那么删除路由
    if(r_info->is_invalid && r_info->cached_refcnt==0) free(r_info);
    else r_info->cached_refcnt-=1;

    DBG("delete route cache\r\n");
	free(cache);
}

static void ixc_route_cache_add(unsigned char *address,int is_ipv6,struct ixc_route_info *r_info)
{
	struct map *m=is_ipv6?route.ip6_rt_cache:route.ip_rt_cache;
	struct ixc_route_cache *cache;
    struct time_data *tdata;
	int rs;

    // 限制路由被缓存引用的数目
    if(r_info->cached_refcnt>=0xffff) return;

    cache=malloc(sizeof(struct ixc_route_cache));

	if(NULL==cache){
		STDERR("no memory,cannot add to route cache\r\n");
		return;
	}

    bzero(cache,sizeof(struct ixc_route_cache));
	
	cache->r_info=r_info;

	if(is_ipv6) memcpy(cache->address,address,16);
	else memcpy(cache->address,address,4);

	cache->is_ipv6=is_ipv6;

	rs=map_add(m,(char *)address,cache);
	if(0!=rs){
		free(cache);
		STDERR("cannot add to route cache\r\n");
		return;
	}

	// add to time wheel
    tdata=time_wheel_add(&route_cache_tw,cache,IXC_IO_WAIT_TIMEOUT);
    if(NULL==tdata){
        STDERR("cannot add to time wheel\r\n");
        map_del(m,(char *)address,NULL);
        free(cache);
        return;
    }

    DBG("add to route cache\r\n");
    cache->tdata=tdata;
    cache->up_time=time(NULL);

	r_info->cached_refcnt+=1;
}

/// 获取缓存
static struct ixc_route_info *ixc_route_cache_get(unsigned char *address,int is_ipv6)
{
    char is_found;
    struct map *m=is_ipv6?route.ip6_rt_cache:route.ip_rt_cache;
    struct ixc_route_cache *cache=map_find(m,(char *)address,&is_found);
    struct time_data *tdata;

    if(NULL!=cache){
        if(!cache->r_info->is_invalid) {
            return cache->r_info;
        }
        // 路由无效那么删除相关内存
        tdata=cache->tdata;
        if(NULL!=tdata) tdata->is_deleted=1;
        map_del(m,(char *)address,ixc_route_cache_del_cb);

        return NULL;
    }

    return NULL;
}

static void ixc_route_sysloop_fn(struct sysloop *loop)
{
    time_wheel_handle(&route_cache_tw);
}

static void ixc_route_cache_timeout(void *data)
{
    time_t now=time(NULL);
    struct ixc_route_cache *cache=data;
    struct map *m=cache->is_ipv6?route.ip6_rt_cache:route.ip_rt_cache;
    struct time_data *tdata;

    if(now-cache->up_time>=IXC_ROUTE_CACHE_TIMEOUT){
        map_del(m,(char *)cache->address,ixc_route_cache_del_cb);
        return;
    }

    tdata=time_wheel_add(&route_cache_tw,cache,IXC_IO_WAIT_TIMEOUT);
    if(NULL==tdata){
        STDERR("cannot get time data\t\n");
        map_del(m,(char *)cache->address,ixc_route_cache_del_cb);
        return;
    }
    
    cache->tdata=tdata;
}

int ixc_route_init(void)
{
    struct map *m;
    int rs;

    bzero(&route,sizeof(struct ixc_route));

    route_sysloop=sysloop_add(ixc_route_sysloop_fn,NULL);
    if(NULL==route_sysloop){
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }

    rs=time_wheel_new(&route_cache_tw,IXC_ROUTE_CACHE_TIMEOUT*2/IXC_IO_WAIT_TIMEOUT,IXC_IO_WAIT_TIMEOUT,ixc_route_cache_timeout,256);
    if(rs<0){
        sysloop_del(route_sysloop);
        STDERR("cannot create new time wheel\r\n");
        return -1;
    }

    rs=map_new(&m,5);
    if(rs){
        sysloop_del(route_sysloop);
        time_wheel_release(&route_cache_tw);
        STDERR("ceate ipv4 map failed\r\n");
        return -1;
    }

    route.ip_rt=m;
    
    rs=map_new(&m,17);
    if(rs){
        sysloop_del(route_sysloop);
        time_wheel_release(&route_cache_tw);
        map_release(route.ip_rt,NULL);
        STDERR("create ipv6 map failed\r\n");
        return -1;
    }
    route.ip6_rt=m;

    rs=map_new(&m,4);
    if(rs){
        sysloop_del(route_sysloop);
        time_wheel_release(&route_cache_tw);
        map_release(route.ip6_rt,NULL);
        map_release(route.ip6_rt,NULL);
        STDERR("create IP cache map failed\r\n");
        return -1;
    }

    route.ip_rt_cache=m;

    rs=map_new(&m,16);
    if(rs){
        sysloop_del(route_sysloop);
        time_wheel_release(&route_cache_tw);
        map_release(route.ip6_rt,NULL);
        map_release(route.ip6_rt,NULL);
        map_release(route.ip_rt_cache,NULL);
        STDERR("create IP cache map failed\r\n");
        return -1;
    }

    route.ip6_rt_cache=m;

    return 0;
}

void ixc_route_uninit(void)
{
    // 注意缓存删除一定要在路由表删除之后,否则会造成内存错误
    // 删除路由条目是会先检查路由是否被缓存,如果被缓存那么保存的路由信息不会被删除,真正会被删除的是在清除缓存后
    map_release(route.ip_rt,ixc_route_del_cb);
    map_release(route.ip6_rt,ixc_route_del_cb);

    map_release(route.ip_rt_cache,ixc_route_cache_del_cb);
    map_release(route.ip6_rt_cache,ixc_route_cache_del_cb);

    sysloop_del(route_sysloop);

    time_wheel_release(&route_cache_tw);

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

    /**
    if(NULL==netif){
        if(is_ipv6){
            IXC_PRINT_IP6("route forward to application for subnet ",r->subnet);
            IXC_PRINT_IP6("route forward to application for key ",key);
            DBG("IPv6 route forward to application prefix %d\r\n",prefix);
        }else{
            IXC_PRINT_IP("route forward to application for subnet ",r->subnet);
        }
    }**/

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
    //unsigned char *t;
    r=ixc_route_cache_get(ip,is_ipv6);
    if(NULL!=r) return r;

    while(NULL!=p){
        
        //DBG_FLAGS;
        subnet_calc_with_msk(ip,p->mask,is_ipv6,(unsigned char *)key);
        //t=(unsigned char *)key;
        //IXC_PRINT_IP("-- ",t);
        //IXC_PRINT_IP("mask ",p->mask);
        //DBG("prefix %d\r\n",p->prefix);
        key[idx]=p->prefix;
        r=map_find(m,key,&is_found);

        /**
        if(is_ipv6){
            IXC_PRINT_IP6("route mask ",p->mask);
            IXC_PRINT_IP6("route find ",ip);
            IXC_PRINT_IP6("route find key ",key);
        }**/

        if(r) break;
        p=p->next;
    }

    // 如果存在该路由那么将路由加入到缓存中
    if(NULL!=r) ixc_route_cache_add(ip,is_ipv6,r);

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

static void ixc_route_ipv6_pass_do(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;
    // 此处执行IPv6透传
    netif=netif->type==IXC_NETIF_WAN?ixc_netif_get(IXC_NETIF_LAN):ixc_netif_get(IXC_NETIF_WAN);
    m->netif=netif;
    m->passthrough=1;

    /// 发送数据包
    if(m->from==IXC_MBUF_FROM_LAN){
        ixc_src_filter_handle(m);
    }else{
        ixc_addr_map_handle(m);
    }
}

static void ixc_route_handle_for_ipv6_local(struct ixc_mbuf *m,struct netutil_ip6hdr *header)
{

    struct ixc_mbuf *clone_m;
    struct netutil_ip6hdr *clone_header;

    //DBG_FLAGS;
    // 只支持ICMPv6协议
    if(header->next_header!=58){
        ixc_mbuf_put(m);
        return;
    }

    // 如果没有开启IPv6透传那么处理ICMPv6
    if(!ixc_route_is_enabled_ipv6_pass()){
        //DBG_FLAGS;
        ixc_icmpv6_handle(m,header);
        return;
    }
    
    // 先修改再克隆,一些透传参数要修改,比如DNS
    ixc_icmpv6_filter_and_modify(m);

    clone_m=ixc_mbuf_clone(m);
    if(NULL!=clone_m){
        clone_header=(struct netutil_ip6hdr *)(clone_m->data+clone_m->offset);
        ixc_icmpv6_handle(clone_m,clone_header);
    }

    ixc_route_ipv6_pass_do(m);
}

static void ixc_route_handle_for_ipv6(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_route_info *r=NULL;
    struct ixc_netif *netif=m->netif;

    m->link_proto=0x86dd;

    // 检查地址是否可以被转发
    if(header->dst_addr[0]==0xff){
        ixc_route_handle_for_ipv6_local(m,header);
        return;
    }

    if(header->dst_addr[0]==0xfe && (header->dst_addr[1] & 0xc0)==0x80){
        ixc_route_handle_for_ipv6_local(m,header);
        return;
    }

    route_modify_ip6_tcp_mss(header);

    // 检查IP地址是否指向自己
    if(!memcmp(header->dst_addr,netif->ip6addr,16)){
        ixc_route_handle_for_ipv6_local(m,header);
        return;
    }    
    //IXC_PRINT_IP6("PRINT IP6",header->dst_addr);
    r=ixc_route_match(header->dst_addr,1);

    //DBG_FLAGS;
    if(NULL!=r){
        // 检查hop limit
        if(header->hop_limit<=1){
            ixc_icmpv6_send_error_msg(netif,m->src_hwaddr,header->src_addr,3,0,0,header,m->tail-m->offset);
            ixc_mbuf_put(m);
            return;
        }

        // 如果没有网卡,那么发送到其他应用
        if(NULL==r->netif){
            IXC_PRINT_IP6("Send to app for ipv6 address ",header->dst_addr);
            //ixc_router_send(netif->type,header->next_header,IXC_FLAG_ROUTE_FWD,m->data+m->offset,m->tail-m->offset);
            // 这里丢弃数据包,避免内存泄漏
            //ixc_mbuf_put(m);
            m->begin=m->offset;
            ixc_npfwd_send_raw(m,header->next_header,IXC_FLAG_ROUTE_FWD);
            return;
        }else{
            netif=r->netif;
        }
    }else{
        if(route.ipv6_pass){
            if(!ixc_ip6sec_check_ok(m)){
                ixc_mbuf_put(m);
                return;
            }
            ixc_route_ipv6_pass_do(m);
        }else{
            ixc_icmpv6_send_error_msg(netif,m->src_hwaddr,header->src_addr,1,3,0,header,m->tail-m->offset);
            ixc_mbuf_put(m);
        }
        return;
    }

    if(!ixc_ip6sec_check_ok(m)){
        ixc_mbuf_put(m);
        return;
    }

    m->netif=netif;
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
        ixc_addr_map_handle(m);
    }
}

/// @ ip地址是否可以被路由检查
/// @param header 
/// @return 1表示可以被路由,0表示无法被路由
static int ixc_route_ip_can_be_routed(struct netutil_iphdr *header)
{
    // 多播地址丢弃
    if((header->dst_addr[0] & 0xf0)==224){
        return 0;
    }
    // 链路本地地址丢弃数据包
    if(header->dst_addr[0]==169 && header->dst_addr[1]==254){
        return 0;
    }
    //未指定地址丢弃 
    if(!memcmp(header->src_addr,IXC_IPADDR_UNSPEC,4)){
        return 0;
    }

    // 广播地址丢弃
    if(!memcmp(header->dst_addr,IXC_IPADDR_BROADCAST,4)){
        return 0;
    }

    return 1;
}

static void ixc_route_handle_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_route_info *r;
    struct ixc_netif *netif=m->netif;

    unsigned short ttl;
    unsigned short csum;

    if(!ixc_route_ip_can_be_routed(iphdr)){
        ixc_mbuf_put(m);
        return;
    }

    route_modify_ip_tcp_mss(iphdr);

    r=ixc_route_match(iphdr->dst_addr,0);

    // 如果找不到路由,那么就丢弃数据包
    if(NULL==r){
        IXC_PRINT_IP("route not found for dest ip",iphdr->dst_addr);
        ixc_mbuf_put(m);
        return;
    }

    //IXC_PRINT_IP("route found for dest ip",iphdr->dst_addr);
    //IXC_PRINT_IP("macth route ",r->subnet);

    // 如果ttl为1那么发送ICMP报文告知
    if(iphdr->ttl<=1){
        ixc_icmp_send_time_ex_msg(netif->ipaddr,iphdr->src_addr,0,iphdr,m->tail-m->offset);
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
        //ixc_router_send(netif->type,iphdr->protocol,IXC_FLAG_ROUTE_FWD,m->data+m->offset,m->tail-m->offset);
        // 这里丢弃数据包,避免内存泄漏
        //ixc_mbuf_put(m);
        //IXC_PRINT_IP("redirect ip packet for dst ",iphdr->dst_addr);
        m->begin=m->offset;
        m->end=m->tail;
        ixc_npfwd_send_raw(m,iphdr->protocol,IXC_FLAG_ROUTE_FWD);
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

inline
int ixc_route_is_enabled_ipv6_pass(void)
{
    return route.ipv6_pass;
}

int ixc_route_ipv6_pass_enable(int enable)
{
    route.ipv6_pass=enable;

    return 0;
}

int ixc_route_tcp_mss_set(unsigned short mss,int is_ipv6)
{
    // 如果tcp mss为0那么就是默认行为
    if(0==mss) {
        if(is_ipv6) route.ip6_tcp_mss=0;
        else route.ip_tcp_mss=0;
        return 1;
    }
    // 限制IPv6的tcp mss
    if(is_ipv6 && mss>1440) {
        STDERR("wrong IPv6 TCP MSS value %u\r\n",mss);
        return 0;
    }
    if(is_ipv6 && mss<516){
        STDERR("wrong IPv6 TCP MSS value %u\r\n",mss);
        return 0;
    }

    if(!is_ipv6 && mss>1460) {
        STDERR("wrong IPv6 TCP MSS value %u\r\n",mss);
        return 0;
    }

    if(!is_ipv6 && mss<536){
        STDERR("wrong IPv6 TCP MSS value %u\r\n",mss);
        return 0;
    }

    if(is_ipv6) route.ip6_tcp_mss=mss;
    else route.ip_tcp_mss=mss;

    return 1;
}