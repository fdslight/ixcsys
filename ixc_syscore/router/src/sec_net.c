#include<string.h>

#include "sec_net.h"
#include "route.h"
#include "router.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_sec_net sec_net;
static int sec_net_is_initialized=0;

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
            ixc_route_handle(m);
        }
        return;
    }
    
    // 检查匹配之后的规则
    if(IXC_SEC_NET_ACT_DROP==dst_rule->action){
        ixc_mbuf_put(m);
    }else{
        ixc_route_handle(m);
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
        ixc_route_handle(m);
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
        STDERR("no memory for create map\r\n");
        return -4;
    }

    return 0;
}

/// 删除源端过滤规则L1
void ixc_sec_net_del_src(unsigned char *hwaddr)
{

}

/// 加入目标过滤规则
int ixc_sec_net_add_dst(unsigned char *hwaddr,unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    return 0;
}

/// 删除目标过滤规则
void ixc_sec_net_del_dst(unsigned char *hwaddr,unsigned char *subnet,unsigned char prefix,int is_ipv6)
{

}