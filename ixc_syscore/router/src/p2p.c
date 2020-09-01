

#include "p2p.h"
#include "ether.h"
#include "nat.h"
#include "natv6.h"

static int p2p_enable=0;

static void ixc_p2p_send(struct ixc_mbuf *m)
{
    if(m->is_ipv6) ixc_natv6_handle(m);
    else ixc_nat_handle(m);
}

int ixc_p2p_init(void)
{
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