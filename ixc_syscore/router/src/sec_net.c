

#include "sec_net.h"
#include "route.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_sec_net sec_net;
static int sec_net_is_initialized=0;

int ixc_sec_net_init(void)
{
    bzero(&sec_net,sizeof(struct ixc_sec_net));

    return 0;
}

void ixc_sec_net_uninit(void)
{

}


static void ixc_sec_net_handle_L2_rule(struct ixc_mbuf *m,struct ixc_sec_net_src_rule_L2 *L2_rule)
{
    struct ixc_sec_net_dst_rule *dst_rule=L2_rule->dst_rule_head;
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    int is_matched=0;
    unsigned char *address=m->is_ipv6?ip6hdr->dst_addr:iphdr->dst_addr;

    while(NULL!=dst_rule){
        is_matched=is_same_subnet_with_msk(address,dst_rule->address,dst_rule->mask,m->is_ipv6);
        if(!is_matched){
            dst_rule=dst_rule->next;
            continue;
        }
        break;
    }

    if(!is_matched){
        if(IXC_SEC_NET_ACT_DROP==L2_rule->action){
            ixc_mbuf_put(m);
        }else{
            ixc_route_handle(m);
        }
        return;
    }

    // 处理匹配的情况
    if(IXC_SEC_NET_ACT_DROP==dst_rule->action){
        ixc_mbuf_put(m);
        return;
    }

    ixc_route_handle(m);
}

static void ixc_sec_net_handle_L1_rule(struct ixc_mbuf *m,struct ixc_sec_net_src_rule_L1 *L1_rule)
{
    struct map *m=m->is_ipv6?L1_rule->ip6_m:L1_rule->ip_m;
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct ixc_sec_net_src_rule_L2 *L2_rule;
    char is_found;
    unsigned char *key=m->is_ipv6?ip6hdr->src_addr:iphdr->src_addr;

    L2_rule=map_find(m,(char *)key,&is_found);

    if(NULL==L2_rule){
        if(IXC_SEC_NET_ACT_DROP==L1_rule->action){
            // 默认丢弃数据包未找到规则那么丢弃数据包
            ixc_mbuf_put(m);
        }else{
            // 默认不为丢弃那么接受该数据包
            ixc_route_handle(m);
        }
        return;
    }

    ixc_sec_net_handle_L2_rule(m,L2_rule);
}

void ixc_sec_net_handle_from_lan(struct ixc_mbuf *m)
{
    unsigned char unspec_hwaddr[]={
        0xff,0xff,0xff,
        0xff,0xff,0xff
    };
    char is_found;
    struct ixc_sec_net_src_rule_L1 *src_L1_rule;

    // 首先检查硬件规则是否存在
    src_L1_rule=map_find(sec_net.rule,(char *)(m->src_hwaddr),&is_found);
    if(NULL==src_L1_rule) src_L1_rule=map_find(sec_net.rule,(char *)unspec_hwaddr,&is_found);

    // 找不到规则那么就通过
    if(NULL==src_L1_rule){
        ixc_route_handle(m);
        return;
    }
    ixc_sec_net_handle_L1_rule(m,src_L1_rule);
}

/// 加入源端过滤规则L1
int ixc_sec_net_add_src_L1(unsigned char *hwaddr,int action)
{
    return 0;
}

/// 删除源端过滤规则L1
void ixc_sec_net_del_src_L1(unsigned char *hwaddr)
{

}

/// 加入源端过滤规则L2
int ixc_sec_net_add_src_L2(unsigned char *hwaddr,unsigned char *address,int is_ipv6)
{
    return 0;
}

/// 删除源端过滤规则L2
void ixc_sec_net_del_src_L2(unsigned char *hwaddr,unsigned char *address,int is_ipv6)
{

}

/// 加入目标过滤规则
int ixc_sec_net_add_dst(unsigned char *id,unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    return 0;
}
/// 删除目标过滤规则
void ixc_sec_net_del_dst(unsigned char *id,unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    
}