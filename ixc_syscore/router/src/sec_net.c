#include<string.h>
#include<time.h>

#include "sec_net.h"
#include "route.h"
#include "router.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"
#include "../../../pywind/clib/timer.h"

static struct ixc_sec_net sec_net;
static struct time_wheel sec_net_cache_tw;
static struct sysloop *sec_net_sysloop=NULL;
static int sec_net_is_initialized=0;

static void __ixc_sec_net_cache_del(void *data)
{
    struct ixc_sec_net_rule_cache *cache=data;
    struct time_data *tdata=cache->tdata;
    
    if(NULL!=tdata) tdata->is_deleted=1;
    // 回收内存
    free(cache);
}

static void __ixc_sec_net_src_rule_del(void *data)
{
    struct ixc_sec_net_src_rule *rule=data;
    struct ixc_sec_net_dst_rule *dst_rules[2];
    struct ixc_sec_net_dst_rule *dst_rule,*t;

    dst_rules[0]=rule->v4_dst_rule_head;
    dst_rules[1]=rule->v6_dst_rule_head;

    // 首先清除所有缓存
    map_release(rule->ip_cache,__ixc_sec_net_cache_del);
    map_release(rule->ip6_cache,__ixc_sec_net_cache_del);

    // 清除所有的的目标规则
    for(int n=0;n<2;n++){
        dst_rule=dst_rules[n];
        while(NULL!=dst_rule){
            t=dst_rule->next;
            free(dst_rule);
            dst_rule=t;
        }
    }

    free(rule);   
}

static void __ixc_sec_net_cache_timeout(void *data)
{
    struct ixc_sec_net_rule_cache *cache=data;
    struct ixc_sec_net_src_rule *src_rule=cache->src_rule;
    struct time_data *tdata=NULL;

    time_t now=time(NULL);

    if(now-cache->up_time>=IXC_SEC_NET_CACHE_TIMEOUT){
        if(cache->is_ipv6) map_del(src_rule->ip6_cache,(char *)cache->address,__ixc_sec_net_cache_del);
        else map_del(src_rule->ip_cache,(char *)cache->address,__ixc_sec_net_cache_del);
        return;
    }

    tdata=time_wheel_add(&sec_net_cache_tw,cache,IXC_IO_WAIT_TIMEOUT);
    if(NULL==tdata){
        cache->tdata=NULL;
        if(cache->is_ipv6) map_del(src_rule->ip6_cache,(char *)cache->address,__ixc_sec_net_cache_del);
        else map_del(src_rule->ip_cache,(char *)cache->address,__ixc_sec_net_cache_del);
        STDERR("cannot add to time wheel\r\n");
        return;
    }
    
    cache->tdata=tdata;
}

static void __ixc_sec_net_sysloop_fn(struct sysloop *loop)
{
    time_wheel_handle(&sec_net_cache_tw);
}

int ixc_sec_net_init(void)
{
    struct map *rule_m;
    int rs;

    bzero(&sec_net,sizeof(struct ixc_sec_net));

    sec_net_sysloop=sysloop_add(__ixc_sec_net_sysloop_fn,NULL);
    if(NULL==sec_net_sysloop){
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }

    rs=time_wheel_new(&sec_net_cache_tw,(IXC_SEC_NET_CACHE_TIMEOUT*2)/IXC_IO_WAIT_TIMEOUT,IXC_IO_WAIT_TIMEOUT,__ixc_sec_net_cache_timeout,128);
    if(rs<0){
        sysloop_del(sec_net_sysloop);
        STDERR("cannot create new time wheel\r\n");
        return -1;
    }

    rs=map_new(&rule_m,6);

    if(rs<0){
        sysloop_del(sec_net_sysloop);
        time_wheel_release(&sec_net_cache_tw);
        STDERR("cannot create rule map for rule\r\n");
        return -1;
    }

    sec_net.rule_m=rule_m;

    sec_net_is_initialized=1;
    return 0;
}

void ixc_sec_net_uninit(void)
{
    if(!sec_net_is_initialized) return;

    map_release(sec_net.rule_m,__ixc_sec_net_src_rule_del);
    sec_net_is_initialized=0;
}

/// 加入到缓存
static int ixc_sec_net_add_to_cache(struct ixc_mbuf *m,struct ixc_sec_net_src_rule *src_rule,int action)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_sec_net_rule_cache *cache=NULL;
    struct map *mm=m->is_ipv6?src_rule->ip6_cache:src_rule->ip_cache;
    char is_found;
    unsigned char *addr=m->is_ipv6?ip6hdr->dst_addr:iphdr->dst_addr;
    struct time_data *tdata;
    int size=m->is_ipv6?16:4,rs;
    // 首先检查缓存是否存在
    cache=map_find(mm,(char *)addr,&is_found);
    // 如果缓存存在那么直接返回
    if(NULL!=cache) return 0;

    cache=malloc(sizeof(struct ixc_sec_net_rule_cache));
    if(NULL==cache){
        STDERR("cannot malloc struct ixc_sec_net_rule_cache\r\n");
        return -1;
    }
    bzero(cache,sizeof(struct ixc_sec_net_rule_cache));

    memcpy(cache->address,addr,size);

    cache->action=action;
    cache->up_time=time(NULL);
    cache->is_ipv6=m->is_ipv6;
    cache->src_rule=src_rule;

    tdata=time_wheel_add(&sec_net_cache_tw,cache,IXC_IO_WAIT_TIMEOUT);
    if(NULL==tdata){
        STDERR("cannot add to time wheel\r\n");
        free(cache);
        return -1;
    }

    rs=map_add(mm,(char *)addr,cache);

    if(rs<0){
        free(cache);
        tdata->is_deleted=1;
        STDERR("cannto add to map\r\n");
        return -1;
    }

    cache->tdata=tdata;

    return 0;
}

static void ixc_sec_net_handle_rule(struct ixc_mbuf *m,struct ixc_sec_net_src_rule *rule)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_sec_net_dst_rule *dst_rule=m->is_ipv6?rule->v6_dst_rule_head:rule->v4_dst_rule_head;
    unsigned char *addr=m->is_ipv6?ip6hdr->dst_addr:iphdr->dst_addr;
    int is_matched=0;
    char is_found;
    struct ixc_sec_net_rule_cache *cache;
    struct map *mm=m->is_ipv6?rule->ip6_cache:rule->ip_cache;
    
    // 首先查找缓存是否存在
    cache=map_find(mm,(char *)addr,&is_found);
    if(NULL!=cache){
        cache->up_time=time(NULL);
        if(IXC_SEC_NET_ACT_DROP==cache->action){
            ixc_mbuf_put(m);
        }else{
            ixc_route_handle(m);
        }
        return;
    }

    while(NULL!=dst_rule){
        is_matched=is_same_subnet_with_msk(addr,dst_rule->address,dst_rule->mask,m->is_ipv6);
        if(!is_matched){
            dst_rule=dst_rule->next;
            continue;
        }
        break;
    }

    if(!is_matched){
        if(IXC_SEC_NET_ACT_DROP==rule->action){
            ixc_sec_net_add_to_cache(m,rule,IXC_SEC_NET_ACT_DROP);
            ixc_mbuf_put(m);
        }else{
            ixc_sec_net_add_to_cache(m,rule,IXC_SEC_NET_ACT_ACCEPT);
            ixc_route_handle(m);
        }
        return;
    }

    if(IXC_SEC_NET_ACT_DROP==dst_rule->action){
        ixc_sec_net_add_to_cache(m,rule,IXC_SEC_NET_ACT_DROP);
        ixc_mbuf_put(m);
    }else{
        ixc_sec_net_add_to_cache(m,rule,IXC_SEC_NET_ACT_ACCEPT);
        ixc_route_handle(m);
    }
}

void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m)
{
    unsigned char unspec_hwaddr[]={
        0x00,0x00,0x00,
        0x00,0x00,0x00
    };
    char is_found;
    struct ixc_sec_net_src_rule *src_rule;

    // 首先检查硬件规则是否存在
    src_rule=map_find(sec_net.rule_m,(char *)(m->src_hwaddr),&is_found);
    if(NULL==src_rule) src_rule=map_find(sec_net.rule_m,(char *)unspec_hwaddr,&is_found);

    // 找不到规则那么就通过
    if(NULL==src_rule){
        //DBG_FLAGS;
        ixc_route_handle(m);
        return;
    }

    //DBG_FLAGS;
    ixc_sec_net_handle_rule(m,src_rule);
}

/// 加入源端过滤规则
int ixc_sec_net_add_src(unsigned char *hwaddr,int action)
{
    char is_found;
    struct ixc_sec_net_src_rule *rule=map_find(sec_net.rule_m,(char *)hwaddr,&is_found);
    struct map *m1,*m2;
    int rs;

    if(NULL!=rule){
        DBG("rule exists\r\n");
        return -1;
    }

    rule=malloc(sizeof(struct ixc_sec_net_src_rule));
    if(NULL==rule){
        DBG("cannot malloc for struct ixc_sec_net_src_rule_L1\r\n");
        return -2;
    }

    bzero(rule,sizeof(struct ixc_sec_net_src_rule));
    rule->action=action;
    memcpy(rule->hwaddr,hwaddr,6);

    rs=map_add(sec_net.rule_m,(char *)hwaddr,rule);
    if(rs<0){
        STDERR("cannot add source rule\r\n");
        return -1;
    }

    rs=map_new(&m1,4);
    if(rs<0){
        free(rule);
        map_del(sec_net.rule_m,(char *)hwaddr,NULL);
        STDERR("no memory for create map\r\n");
        return -3;
    }
    rs=map_new(&m2,16);
    if(rs<0){
        free(rule);
        map_release(m1,NULL);
        map_del(sec_net.rule_m,(char *)hwaddr,NULL);
        STDERR("no memory for create map\r\n");
        return -4;
    }

    rule->ip_cache=m1;
    rule->ip6_cache=m2;

    return 0;
}

/// 删除源端过滤规则
void ixc_sec_net_del_src(unsigned char *hwaddr)
{
    char is_found;
    struct ixc_sec_net_src_rule *rule=map_find(sec_net.rule_m,(char *)hwaddr,&is_found);
    if(NULL==rule) return;
    map_del(sec_net.rule_m,(char *)hwaddr,__ixc_sec_net_src_rule_del);
}

/// 加入目标过滤规则
int ixc_sec_net_add_dst(unsigned char *hwaddr,unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    char is_found;
    struct ixc_sec_net_src_rule *src_rule=map_find(sec_net.rule_m,(char *)hwaddr,&is_found);
    struct ixc_sec_net_dst_rule *dst_rule;
    int exists=0;
    int size=is_ipv6?16:4;

    if(NULL==src_rule){
        STDERR("not found source rule\r\n");
        return -1;
    }

    dst_rule=is_ipv6?src_rule->v6_dst_rule_head:src_rule->v4_dst_rule_head;

    while(NULL!=dst_rule){
        if(!memcmp(subnet,dst_rule->address,size) && dst_rule->prefix==prefix){
            exists=1;
            break;
        }
        dst_rule=dst_rule->next;
    }
    // 如果存在那么直接返回,不执行添加操作
    if(exists) return 0;

    dst_rule=malloc(sizeof(struct ixc_sec_net_dst_rule));
    if(NULL==dst_rule){
        STDERR("cannot create struct ixc_sec_net_dst_rule\r\n");
        return -2;
    }
    bzero(dst_rule,sizeof(struct ixc_sec_net_dst_rule));

    dst_rule->prefix=prefix;

    msk_calc(prefix,is_ipv6,dst_rule->mask);
    memcpy(dst_rule->address,subnet,size);
    
    // 目标策略与源端策略相反
    if(IXC_SEC_NET_ACT_DROP==src_rule->action){
        dst_rule->action=IXC_SEC_NET_ACT_ACCEPT;
    }else{
        dst_rule->action=IXC_SEC_NET_ACT_DROP;
    }

    if(is_ipv6){
        dst_rule->next=src_rule->v6_dst_rule_head;
        src_rule->v6_dst_rule_head=dst_rule;
    }else{
        dst_rule->next=src_rule->v4_dst_rule_head;
        src_rule->v4_dst_rule_head=dst_rule;
    }

    return 0;
}