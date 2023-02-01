#include "nptv6.h"
#include "netif.h"


#include "../../../pywind/clib/sysloop.h"
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

}