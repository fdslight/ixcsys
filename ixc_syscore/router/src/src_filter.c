#include<string.h>

#include "src_filter.h"
#include "qos.h"
#include "netif.h"
#include "router.h"
#include "global.h"
#include "npfwd.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_src_filter src_filter;

static void ixc_src_filter_send(struct ixc_mbuf *m)
{
    int size;
    char is_found;
    //void *data;
    //int is_subnet,size;
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_ip6hdr *ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset);
    unsigned char ipproto=0,*addr_ptr,*pkt_addr_ptr;

    // 只处理LAN网卡
    if(IXC_MBUF_FROM_LAN!=m->from){
        ixc_qos_add(m);
        return;
    }
    
    if(m->is_ipv6){
        size=16;
        addr_ptr=ixc_g_manage_addr_get(1);
        pkt_addr_ptr=ip6hdr->src_addr;
    }else{
        size=4;
        addr_ptr=ixc_g_manage_addr_get(0);
        pkt_addr_ptr=iphdr->src_addr;
    }

    // 如果是本机的数据包那么就跳过
    if(!memcmp(addr_ptr,pkt_addr_ptr,size)){
        ixc_qos_add(m);
        return;
    }

    if(m->is_ipv6) {
        ipproto=ip6hdr->next_header;
        if(!src_filter.protocols[ipproto]){
            ixc_qos_add(m);
            return;
        }
        //is_subnet=is_same_subnet_with_msk(ip6hdr->src_addr,src_filter.ip6_subnet,src_filter.ip6_mask,1);
        
    }else{
        ipproto=iphdr->protocol;
        if(!src_filter.protocols[ipproto]){
            ixc_qos_add(m);
            return;
        }
        //is_subnet=is_same_subnet_with_msk(iphdr->src_addr,src_filter.ip_subnet,src_filter.ip_mask,0);
    }

    // 不在要求的地址范围内那么直接发送到下一个节点
    /*if(!is_subnet){
        ixc_qos_add(m);
        return;
    }*/
    map_find(src_filter.map,(char *)(m->src_hwaddr),&is_found);
    if(!is_found){
        ixc_qos_add(m);
        return;
    }
    //ixc_router_send(netif->type,ipproto,IXC_FLAG_SRC_FILTER,m->data+m->offset,m->tail-m->offset);
    ixc_npfwd_send_raw(m,ipproto,IXC_FLAG_SRC_FILTER);
}

int ixc_src_filter_init(void)
{
    struct map *m;
    int rs=map_new(&m,6);

    bzero(&src_filter,sizeof(struct ixc_src_filter));

    if(0!=rs){
        STDERR("cannot init map\r\n");
        return -1;
    }

    src_filter.map=m;
   
    return 0;
}

void ixc_src_filter_uninit(void)
{
    if(NULL!=src_filter.map){
        map_release(src_filter.map,NULL);
    }
    src_filter.is_opened=0;
}

int ixc_src_filter_enable(int enable)
{
    src_filter.is_opened=enable;

    return 0;
}

int ixc_src_filter_add_hwaddr(const unsigned char *hwaddr)
{
    char is_found;
    int rs;
    
    map_find(src_filter.map,(char *)hwaddr,&is_found);
    if(is_found) return 1;

    rs=map_add(src_filter.map,(char *)hwaddr,NULL);
    if(0!=rs) return 0;

    return 1;
}

void ixc_src_filter_del_hwaddr(const unsigned char *hwaddr)
{
    map_del(src_filter.map,(char *)hwaddr,NULL);
}

/*
int ixc_src_filter_set_ip(unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    unsigned char result[16];
    int size=is_ipv6?16:4;
    subnet_calc_with_prefix(subnet,prefix,is_ipv6,result);

    if(memcmp(subnet,result,size)) return -1;

    if(is_ipv6){
        memcpy(src_filter.ip6_subnet,subnet,16);
        msk_calc(prefix,1,src_filter.ip6_mask);
    }else{
        memcpy(src_filter.ip_subnet,subnet,4);
        msk_calc(prefix,0,src_filter.ip_mask);
    }

    return 0;
}*/

int ixc_src_filter_set_protocols(unsigned char *protocols)
{
    memcpy(src_filter.protocols,protocols,0xff);
    return 0;
}

void ixc_src_filter_handle(struct ixc_mbuf *m)
{
    // 如果没启用源地址协议过滤,那么直接发送数据
    if(!src_filter.is_opened) {
        ixc_qos_add(m);
    }else{
        ixc_src_filter_send(m);
    }
}