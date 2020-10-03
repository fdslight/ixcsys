

#include "ip6.h"


void ixc_ip6_handle(struct ixc_mbuf *mbuf)
{
    mbuf->is_ipv6=1;
    ixc_mbuf_put(mbuf);
}

int ixc_ip6_send(struct ixc_mbuf *mbuf)
{
    mbuf->is_ipv6=1;
    
    ixc_mbuf_put(mbuf);

    return 0;
}