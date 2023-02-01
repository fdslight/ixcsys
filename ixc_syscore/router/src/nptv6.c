#include "nptv6.h"
#include "netif.h"

#include "../../../pywind/clib/netutils.h"

/// 是否开启IPv6前缀转换
static int nptv6_is_enabled=0;

int ixc_nptv6_init(void)
{
    nptv6_is_enabled=0;
    return 0;
}

void ixc_nptv6_uninit(void)
{
    nptv6_is_enabled=0;
}

int ixc_nptv6_set_enable(int enable)
{
    nptv6_is_enabled=enable;

    return 0;
}

static void __ixc_nptv6_convert(struct ixc_mbuf *m)
{
    struct ixc_netif *if_lan=ixc_netif_get(IXC_NETIF_LAN);
    struct ixc_netif *if_wan=ixc_netif_get(IXC_NETIF_WAN);

    struct netutil_ip6hdr *ip6_header=(struct netutil_ip6hdr *)(m->data+m->offset);

    unsigned char *addr,*dst_prefix;
    unsigned short csum_a,csum_b,v;

    int old_prefix_size,new_prefix_size;


    if(IXC_MBUF_FROM_WAN==m->from){
        addr=ip6_header->dst_addr;
        old_prefix_size=if_wan->ip6_prefix;
        new_prefix_size=if_lan->ip6_prefix;
        dst_prefix=if_lan->ip6_mask;
    }else{
        addr=ip6_header->src_addr;
        old_prefix_size=if_lan->ip6_prefix;
        new_prefix_size=if_wan->ip6_prefix;
        dst_prefix=if_wan->ip6_mask;
    }

    if(old_prefix_size % 8 > 0) old_prefix_size= (old_prefix_size / 8 + 1) * 8;
    if(new_prefix_size % 8 > 0) new_prefix_size= (new_prefix_size / 8 + 1) * 8;

    csum_a= csum_calc((unsigned short *)addr,16);
    csum_b= csum_calc((unsigned short *)dst_prefix,new_prefix_size);
    
    v=csum_a-csum_b;

}

void ixc_nptv6_handle(struct ixc_mbuf *m)
{
    struct ixc_netif *if_lan=ixc_netif_get(IXC_NETIF_LAN);
    struct ixc_netif *if_wan=ixc_netif_get(IXC_NETIF_WAN);

    // 内外网未设置IPv6地址那么不处理
    if(!if_lan->isset_ip6 || !if_wan->isset_ip6){
        return;
    }

    // WAN前缀必须要小于112
    if(if_wan->ip6_prefix > 112){
        return;
    }

    __ixc_nptv6_convert(m);

}