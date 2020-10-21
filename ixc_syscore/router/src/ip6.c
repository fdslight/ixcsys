
#include<string.h>

#include "ip6.h"

#include "../../../pywind/clib/netutils.h"


void ixc_ip6_handle(struct ixc_mbuf *mbuf)
{
    //struct netutil_ip6hdr *header;
    if(mbuf->tail-mbuf->offset<40) return;

    //header=(struct netutil_ip6hdr *)(mbuf->data+mbuf->offset);
    // 检查IC
    mbuf->is_ipv6=1;
    ixc_mbuf_put(mbuf);
}

int ixc_ip6_send(struct ixc_mbuf *mbuf)
{
    //struct netutil_ip6hdr *header;
    if(mbuf->tail-mbuf->offset<40) return 0;

    mbuf->is_ipv6=1;
    // /header=(struct netutil_ip6hdr *)(mbuf->data+mbuf->offset);
    
    ixc_mbuf_put(mbuf);

    return 0;
}

int ixc_ip6_eui64_get(unsigned char *hwaddr,unsigned char *result)
{
    unsigned char x;

    result[0]=hwaddr[0];
    result[1]=hwaddr[1];
    result[2]=hwaddr[2];
    result[3]=0xff;
    result[4]=0xfe;
    result[5]=hwaddr[3];
    result[6]=hwaddr[4];
    result[7]=hwaddr[5];

    x=result[7] & 0x02;

    if(x) result[7]=result[7] & 0xfd;
    else result[7]=result[7] & 0xff;

    return 0;
}

int ixc_ip6_local_link_get(unsigned char *hwaddr,unsigned char *result)
{
    memset(result,0x00,16);

    result[0]=0xfe;
    result[1]=0x80;

    ixc_ip6_eui64_get(hwaddr,&result[8]);
    
    return 0;
}

int ixc_ip6_addr_get(unsigned char *hwaddr,unsigned char *subnet,unsigned char *result)
{
    memcpy(result,subnet,16);
    ixc_ip6_eui64_get(hwaddr,&result[8]);

    return 0;
}