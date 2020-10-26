
#include "pppoe.h"
#include "natv6.h"
#include "qos.h"
#include "route.h"
#include "string.h"
#include "netif.h"
#include "addr_map.h"

#include "../../../pywind/clib/debug.h"

static struct ixc_natv6 natv6;
static int natv6_is_initialized=0;

int ixc_natv6_init(void)
{
    bzero(&natv6,sizeof(struct ixc_natv6));
    natv6_is_initialized=1;

    return 0;
}

void ixc_natv6_uninit(void)
{
    natv6_is_initialized=0;
}

static void ixc_natv6_handle_from_lan(struct ixc_mbuf *m)
{
    if(!natv6.enable){
        ixc_addr_map_handle(m);
        return;
    }
    ixc_mbuf_put(m);
}

static void ixc_natv6_handle_from_wan(struct ixc_mbuf *m)
{
    ixc_mbuf_put(m);
}

void ixc_natv6_handle(struct ixc_mbuf *m)
{
    if(!natv6_is_initialized){
        ixc_mbuf_put(m);
        STDERR("NATv6 is not initialized\r\n");
        return;
    }

    // 没有开启NATv6那么直接通过
    if(!natv6.enable){
        if(IXC_MBUF_FROM_LAN==m->from) ixc_natv6_handle_from_lan(m);
        else ixc_natv6_handle_from_wan(m);

        return;
    }

    ixc_mbuf_put(m);
}

int ixc_natv6_enable(int status,int type)
{
    natv6.enable=status;
    natv6.type=type;

    return 0;
}