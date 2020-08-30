

#include "arp.h"

int ixc_arp_send(struct ixc_arp *arp)
{
    return 0;
}

void ixc_arp_handle(struct ixc_mbuf *mbuf)
{
    ixc_mbuf_put(mbuf);
}