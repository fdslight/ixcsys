
#include<string.h>

#include "sec_net.h"
#include "route.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/timer.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_sec_net sec_net;
static int sec_net_is_initialized=0;

int ixc_sec_net_init(void)
{
    struct map *m=NULL;
    int rs;

    bzero(&sec_net,sizeof(struct ixc_sec_net));

    rs=map_new(&m,6);
    if(0!=rs){
        STDERR("cannot create map for log hwaddr\r\n");
        return -1;
    }

    sec_net.log_hwaddr_m=m;


    return 0;
}

void ixc_sec_net_uninit(void)
{
    sec_net_is_initialized=0;
}

int ixc_sec_net_src_rule_add(unsigned char *hwaddr,unsigned char *address,short action,int is_ipv6)
{
    return 0;
}

int ixc_sec_net_src_rule_del(unsigned char *hwaddr,unsigned char *address,int is_ipv6)
{
    return 0;
}

/// 记录日志
static void ixc_sec_net_log_write_and_send(struct ixc_mbuf *m)
{
    ixc_route_handle(m);
}

static struct ixc_sec_net_rule_dst *
ixc_sec_net_find_no_cached(struct ixc_sec_net_rule_src *src,const char *address,int is_ipv6)
{
    return NULL;
}


static void ixc_sec_net_find_dst_rule(struct ixc_mbuf *m,struct ixc_sec_net_rule_src *src)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_sec_net_rule_dst *rule_dst=NULL;
    char key[16],is_found;

    if(m->is_ipv6) memcpy(key,ip6hdr->dst_addr,16);
    else memcpy(key,iphdr->dst_addr,4);

    // 首先从缓存中查找是否存在该规则
    rule_dst=map_find(src->cache_m,key,&is_found);
    // 如果该规则不在缓存中,那么直接查找
    if(NULL!=rule_dst) rule_dst=ixc_sec_net_find_no_cached(src,key,m->is_ipv6);
}

static void ixc_sec_net_handle_src(struct ixc_mbuf *m,struct ixc_sec_net_rule_src *rule)
{
    struct ixc_sec_net_rule_dst *dst_rule,*tmp_dst_rule;
    struct netutil_iphdr *ipdhr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    //
    char key[16],is_found;
    int flags=0;
    // 未找到规则那么接受数据包并且记录日志
    if(NULL==rule){
        ixc_sec_net_log_write_and_send(m);
        return;
    }
    // 拷贝内存响应key
    if(m->is_ipv6) memcpy(key,ip6hdr->dst_addr,16);
    else memcpy(key,ipdhr->dst_addr,4);
    //
    if(IXC_SEC_NET_ACT_DROP==rule->default_action){
        // 默认为丢弃数据包并且未找到允许的地址范围,那么丢弃数据包
        if(NULL==rule->dst_head){
            ixc_mbuf_put(m);
            return;
        }
    }
    // 首先从缓存中查找是否存在
    dst_rule=map_find(rule->cache_m,key,&is_found);
__SEC_NET_DST:
    if(NULL!=dst_rule){
        // 如果默认是丢弃数据包那么规则中含有目标规则,那么就接受此数据包
        if(IXC_SEC_NET_ACT_DROP==rule->default_action){
            ixc_sec_net_log_write_and_send(m);
        }else{
            ixc_mbuf_put(m);
        }
        return;
    }
    //
    if(flags && NULL==dst_rule){
        ixc_sec_net_log_write_and_send(m);
        return;
    }
    // 处理不在缓存中的目标规则
    dst_rule=ixc_sec_net_find_no_cached(rule,key,m->is_ipv6);
    flags=1;
    goto __SEC_NET_DST;
}

static void ixc_sec_net_handle_v4(struct ixc_mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_sec_net_rule_src *rule=NULL;
    char is_found;

    rule=map_find(sec_net.rule_ip_m,(char *)(header->src_addr),&is_found);

    ixc_sec_net_handle_src(m,rule);
}

static void ixc_sec_net_handle_v6(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_sec_net_rule_src *rule=NULL;
    char is_found;

    rule=map_find(sec_net.rule_ip6_m,header->src_addr,&is_found);
    ixc_sec_net_handle_src(m,rule);
}

static void ixc_sec_net_handle_hwaddr_rule(struct ixc_mbuf *m)
{
    struct ixc_sec_net_rule_src *rule=NULL;
    char is_found;

    // 首先查找硬件规则匹配是否存在
    rule=map_find(sec_net.rule_hwaddr_m,(char *)(m->src_hwaddr),&is_found);
    ixc_sec_net_handle_src(m,rule);
}

void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m)
{
    ixc_sec_net_handle_hwaddr_rule(m);
}