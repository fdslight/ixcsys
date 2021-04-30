
#include<string.h>

#include "sec_net.h"

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


static struct ixc_sec_net_rule_dst *
ixc_sec_net_find_no_cached(struct ixc_sec_net_rule_src *src,unsigned char *address,int is_ipv6)
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
    // 未找到规则那么接受数据包
    if(NULL==rule){
        return;
    }
    //
    if(IXC_SEC_NET_ACT_DROP==rule->default_action){
        // 默认为丢弃数据包并且未找到允许的地址范围,那么丢弃数据包
        if(NULL==rule->dst_head){
            ixc_mbuf_put(m);
            return;
        }

    }
}

static void ixc_sec_net_handle_v4(struct ixc_mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_sec_net_rule_src *rule=NULL;
    char is_found;

    rule=map_find(sec_net.rule_ip_m,header->src_addr,&is_found);

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
    rule=map_find(sec_net.rule_hwaddr_m,m->src_hwaddr,&is_found);
    ixc_sec_net_handle_src(m,rule);
}

void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m)
{
    ixc_sec_net_handle_hwaddr_rule(m);
}