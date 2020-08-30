

#include "ip.h"
#include "ip6.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/debug.h"

void ixc_ip_handle(struct ixc_mbuf *mbuf)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(mbuf->data+mbuf->offset);
    int version=(header->ver_and_ihl & 0xf0) >> 4;

    if(4!=version){
        ixc_mbuf_put(mbuf);
        return;
    }

    
}