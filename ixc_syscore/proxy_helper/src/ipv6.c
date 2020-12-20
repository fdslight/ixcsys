#include<string.h>

#include "ipv6.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static int ipv6_mtu=1280;

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

int ipv6_send(unsigned char *src_addr,unsigned char *dst_addr,unsigned char protocol,void *data,unsigned short length)
{
    return 0;
}

int ipv6_mtu_set(unsigned short mtu)
{
    ipv6_mtu=mtu;
    return 0;
}