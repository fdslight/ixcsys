#include<string.h>

#include "icmp.h"
#include "ip.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/debug.h"

static void ixc_icmp_handle_self(struct ixc_mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    int hdr_len= (header->ver_and_ihl & 0x0f) * 4;
    struct netutil_icmphdr *icmphdr=(struct netutil_icmphdr *)(m->data+m->offset+hdr_len);
    unsigned char src_ipaddr[4],dst_ipaddr[4];

    // 只处理echo请求
    if(0!=icmphdr->type && 0!=icmphdr->code){
        ixc_mbuf_put(m);
        return;
    }

    memcpy(src_ipaddr,header->dst_addr,4);
    memcpy(dst_ipaddr,header->src_addr,4);

    rewrite_ip_addr(header,src_ipaddr,1);
    rewrite_ip_addr(header,dst_ipaddr,0);

    ixc_ip_send(m);
}


void ixc_icmp_handle(struct ixc_mbuf *m,int is_self)
{
    if(is_self) ixc_icmp_handle_self(m);
    else ixc_mbuf_put(m);
}