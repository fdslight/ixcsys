

#include "ipv6.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

void ipv6_handle(struct mbuf *m)
{
    int is_supported=0;
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);

    switch(header->next_header){
        case 6:
        case 17:
        case 44:
        case 136:
            is_supported=1;
            break;
        default:
            break;
    }

    if(!is_supported){
        mbuf_put(m);
        return;
    }

}