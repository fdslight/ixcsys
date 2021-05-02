#include<string.h>

#include "sec_net.h"
#include "route.h"
#include "router.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_sec_net sec_net;
static int sec_net_is_initialized=0;

static void __ixc_sec_net_del_dst_rule(struct ixc_sec_net_src_rule *src_rule,unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    struct ixc_sec_net_dst_rule *dst_rule,*dst_rule_old,*first,*del_dst_rule=NULL,*t;
    int size,need_deleted=0;

    if(is_ipv6){
        dst_rule_old=src_rule->v6_dst_rule_head;
        dst_rule=src_rule->v6_dst_rule_head;
        size=16;
    }else{
        dst_rule_old=src_rule->v4_dst_rule_head;
        dst_rule=src_rule->v4_dst_rule_head;
        size=4;
    }
    first=dst_rule;

    while(NULL!=dst_rule){
        // 如果存在那么进行处理
        if(!memcmp(dst_rule->address,subnet,size) && dst_rule->prefix==prefix){
            dst_rule->is_deleted=1;
            // 此处检查缓存计数是否为0,如果不为零那么减少缓存计数
            if(0!=dst_rule->cache_refcnt){
                dst_rule->cache_refcnt-=1;
            }else{
                del_dst_rule=dst_rule;
                need_deleted=1;
            }
            break;
        }
        dst_rule=dst_rule->next;
    }

    // 如果缓存计数不为0那么就不能删除该规则
    if(!need_deleted) return;
    dst_rule=first;

    // 如果是第一个要删除的规则处理
    if(dst_rule==del_dst_rule){
        t=dst_rule->next;
        free(dst_rule);
        if(is_ipv6) src_rule->v6_dst_rule_head=t;
        else src_rule->v4_dst_rule_head=t;
        return;
    }

    while(NULL!=dst_rule){
        if(dst_rule!=del_dst_rule){
            dst_rule_old=dst_rule;
            dst_rule=dst_rule->next;

            continue;
        }

        dst_rule_old->next=dst_rule->next;
        free(dst_rule);
        break;
    }
}

int ixc_sec_net_init(void)
{
    bzero(&sec_net,sizeof(struct ixc_sec_net));

    sec_net_is_initialized=1;
    return 0;
}

void ixc_sec_net_uninit(void)
{
    if(!sec_net_is_initialized) return;

    sec_net_is_initialized=0;
}

static void ixc_sec_net_log_write_and_send(struct ixc_mbuf *m)
{
    ixc_route_handle(m);
}


/// 加入到缓存
static int ixc_sec_net_add_to_cache(struct ixc_mbuf *m,struct ixc_sec_net_dst_rule *dst_rule)
{
    struct ixc_sec_net_src_rule *src_rule=dst_rule->src_rule;
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_sec_net_rule_cache *cache=NULL;
    struct map *m=m->is_ipv6?src_rule->ip6_cache:src_rule->ip_cache;
    char is_found;
    unsigned char *addr=m->is_ipv6?ip6hdr->dst_addr:iphdr->dst_addr;
    int size=m->is_ipv6?16:4,rs;
    // 首先检查缓存是否存在
    cache=map_find(m,(char *)addr,&is_found);
    // 如果缓存存在那么直接返回
    if(NULL!=cache) return 0;

    cache=malloc(sizeof(struct ixc_sec_net_rule_cache));
    if(NULL==cache){
        STDERR("cannot malloc struct ixc_sec_net_rule_cache\r\n");
        return -1;
    }
    memcpy(cache->address,addr,size);

    cache->dst_rule=dst_rule;
    cache->action=dst_rule->action;
    cache->up_time=time(NULL);

    rs=map_add(m,(char *)addr,cache);
    if(rs<0){
        free(cache);
        STDERR("cannto add to map\r\n");
        return -1;
    }

    return 0;
}

static void ixc_sec_net_handle_rule(struct ixc_mbuf *m,struct ixc_sec_net_src_rule *rule)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_sec_net_dst_rule *dst_rule=m->is_ipv6?rule->v6_dst_rule_head:rule->v4_dst_rule_head;
    unsigned char *addr=m->is_ipv6?ip6hdr->dst_addr:iphdr->dst_addr;
    int is_matched=0;

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
            ixc_mbuf_put(m);
        }else{
            ixc_sec_net_log_write_and_send(m);
        }
        return;
    }

    // 检查匹配之后的规则
    if(IXC_SEC_NET_ACT_DROP==dst_rule->action){
        ixc_mbuf_put(m);
    }else{
        ixc_sec_net_log_write_and_send(m);
    }
}

void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m)
{
    unsigned char unspec_hwaddr[]={
        0xff,0xff,0xff,
        0xff,0xff,0xff
    };
    char is_found;
    struct ixc_sec_net_src_rule *src_rule;

    // 首先检查硬件规则是否存在
    src_rule=map_find(sec_net.rule_m,(char *)(m->src_hwaddr),&is_found);
    if(NULL==src_rule) src_rule=map_find(sec_net.rule_m,(char *)unspec_hwaddr,&is_found);

    // 找不到规则那么就通过
    if(NULL==src_rule){
        ixc_sec_net_log_write_and_send(m);
        return;
    }
    ixc_sec_net_handle_rule(m,src_rule);
}

/// 加入源端过滤规则L1
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

    rs=map_new(&m1,4);
    if(rs<0){
        free(rule);
        STDERR("no memory for create map\r\n");
        return -3;
    }
    rs=map_new(&m2,16);
    if(rs<0){
        free(rule);
        map_release(m1,NULL);
        STDERR("no memory for create map\r\n");
        return -4;
    }

    rule->ip_cache=m1;
    rule->ip6_cache=m2;

    return 0;
}

/// 删除源端过滤规则L1
void ixc_sec_net_del_src(unsigned char *hwaddr)
{

}

/// 加入目标过滤规则
int ixc_sec_net_add_dst(unsigned char *hwaddr,unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    char is_found;
    struct ixc_sec_net_src_rule *src_rule=map_find(sec_net.rule_m,(char *)hwaddr,&is_found);
    struct map *m;
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

    dst_rule->src_rule=src_rule;
    dst_rule->prefix=prefix;

    msk_calc(prefix,is_ipv6,dst_rule->mask);
    memcpy(dst_rule->address,subnet,size);
    
    // 目标策略与源端策略相反
    if(IXC_SEC_NET_ACT_DROP==src_rule->action){
        dst_rule->action=IXC_SEC_NET_ACT_ACCEPT;
    }else{
        dst_rule->action=IXC_SEC_NET_ACT_ACCEPT;
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

/// 删除目标过滤规则
void ixc_sec_net_del_dst(unsigned char *hwaddr,unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    char is_found;
    struct ixc_sec_net_src_rule *src_rule=map_find(sec_net.rule_m,(char *)hwaddr,&is_found);
    
    int exists=0;
    int size=is_ipv6?16:4;

    if(NULL==src_rule){
        STDERR("not found source rule\r\n");
        return -1;
    }
    __ixc_sec_net_del_dst_rule(src_rule,subnet,prefix,is_ipv6);
}