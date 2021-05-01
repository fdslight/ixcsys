
#include<string.h>

#include "sec_net.h"
#include "route.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/timer.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_sec_net sec_net;
/// 缓存定时器
static struct time_wheel sec_net_cache_time_wheel;
/// 日志定时器
static struct time_wheel sec_net_log_time_wheel;
static int sec_net_is_initialized=0;

static void __ixc_sec_net_cache_del(void *data)
{

}

static void __ixc_sec_net_cache_timeout(void *data)
{
    struct ixc_sec_net_rule_dst *dst_rule=data;
    time_t now=time(NULL);

    // 大于缓存超时那么删除缓存
    if(now-dst_rule->up_time>IXC_SEC_NET_CACHE_TIMEOUT){
    }

}

static void __ixc_sec_net_log_timeout(void *data)
{

}

int ixc_sec_net_init(void)
{
    struct map *m=NULL;
    int rs;

    bzero(&sec_net,sizeof(struct ixc_sec_net));

    rs=time_wheel_new(&sec_net_cache_time_wheel,(IXC_SEC_NET_CACHE_TIMEOUT*2)/10,10,__ixc_sec_net_cache_timeout,128);

    if(rs<0){
        STDERR("cannot create cache time wheel for sec_net\r\n");
        return -1;
    }

    rs=time_wheel_new(&sec_net_cache_time_wheel,20,10,__ixc_sec_net_log_timeout,128);

    if(rs<0){
        STDERR("cannot create log time wheel for sec_net\r\n");
        return -1;
    }

    rs=map_new(&m,6);
    if(0!=rs){
        time_wheel_release(&sec_net_cache_time_wheel);
        time_wheel_release(&sec_net_log_time_wheel);

        STDERR("cannot create map for log hwaddr\r\n");
        return -1;
    }

    sec_net.log_hwaddr_m=m;

    sec_net_is_initialized=1;
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
ixc_sec_net_find_no_cached(struct ixc_sec_net_rule_src *src,unsigned char *address,int is_ipv6)
{
    struct ixc_sec_net_rule_dst *dst_rule=src->dst_head;
    int is_found=0,rs;
    struct time_data *tdata;

    while(NULL!=dst_rule){
        if(!is_same_subnet_with_msk(address,dst_rule->dst_addr,dst_rule->mask,is_ipv6)){
            dst_rule=dst_rule->next;
            continue;
        }
        is_found=1;
        break;
    }

    if(!is_found) return NULL;

    // 如果找到策略,那么就加入到缓存当中,以便加快访问速度
    rs=map_add(src->cache_m,(char *)address,dst_rule);

    if(rs<0){
        STDERR("cannot add to sec_net cache\r\n");
        return dst_rule;
    }

    tdata=time_wheel_add(&sec_net_cache_time_wheel,dst_rule,10);
    if(NULL==tdata){
        map_del(src->cache_m,(char *)address,NULL);
        STDERR("cannot add to sec_net cache\r\n");
        return dst_rule;
    }

    dst_rule->up_time=time(NULL);
    // 增加引用计数
    dst_rule->refcnt+=1;

    return dst_rule;
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
    if(NULL!=rule_dst) rule_dst=ixc_sec_net_find_no_cached(src,(unsigned char *)key,m->is_ipv6);
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
    dst_rule=ixc_sec_net_find_no_cached(rule,(unsigned char *)key,m->is_ipv6);
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

    rule=map_find(sec_net.rule_ip6_m,(char *)header->src_addr,&is_found);
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