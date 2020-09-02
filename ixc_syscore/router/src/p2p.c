#include<string.h>

#include "p2p.h"
#include "ether.h"
#include "nat.h"
#include "natv6.h"

#include "../../../pywind/clib/debug.h"

static int p2p_enable=0;
static struct ixc_p2p p2p;

static void ixc_p2p_send(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;

    // 只处理LAN网卡
    if(IXC_NETIF_LAN==netif->type){
        // 检查是否在指定的地址范围内
    }

    if(m->is_ipv6) ixc_natv6_handle(m);
    else ixc_nat_handle(m);
}

int ixc_p2p_init(void)
{
    bzero(&p2p,sizeof(struct ixc_p2p));
    return 0;
}

void ixc_p2p_uninit(void)
{
    
}

int ixc_p2p_enable(int enable)
{
    return 0;
}

int ixc_p2p_set(unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    return 0;
}

void ixc_p2p_handle(struct ixc_mbuf *m)
{
    // 如果没启用P2P那么直接发送数据
    if(!p2p_enable) ixc_p2p_send(m);
}