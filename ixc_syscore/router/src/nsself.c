#include "nsself.h"
#include "netif.h"
#include "icmp.h"
#include "debug.h"

#include "../../../pywind/clib/netutils.h"

static int nsself_is_initialized=0;


static void ixc_nsself_handle_for_ipv6(struct ixc_mbuf *m)
{
    ixc_mbuf_put(m);
}

static void ixc_nsself_handle_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);

    switch(iphdr->protocol){
        case 1:
           ixc_icmp_handle_self(m);
            break;
        default:
            ixc_mbuf_put(m);
            break;
    }
}

int ixc_nsself_init(void)
{

    nsself_is_initialized=1;
    return 0;
}

void ixc_nsself_uninit(void)
{
    nsself_is_initialized=0;
}

void ixc_nsself_handle(struct ixc_mbuf *m)
{
    if(!nsself_is_initialized){
        ixc_mbuf_put(m);
        STDERR("not init nsself\r\n");
        return;
    }

    DBG_FLAGS;

    if(m->is_ipv6) ixc_nsself_handle_for_ipv6(m);
    else ixc_nsself_handle_for_ip(m);

}