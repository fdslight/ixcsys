
#include<sys/types.h>
#include <arpa/inet.h>

#include "udp.h"
#include "debug.h"
#include "mbuf.h"
#include "ip.h"
#include "ip6.h"

#include "../../../pywind/clib/netutils.h"

int udp_send(unsigned char *saddr,unsigned char *daddr,unsigned short sport,unsigned short dport,int is_ipv6,int is_udplite,unsigned short csum_coverage,void *data,size_t length)
{
    struct netutil_udphdr udphdr;
    struct netutil_ip6_ps_header ps6_header;
    struct netutil_ip_ps_header ps_header;
    struct mbuf *m=NULL;
    unsigned char p;
    
    bzero(&udphdr,sizeof(struct netutil_udphdr));
    bzero(&ps6_header,sizeof(struct netutil_ip6_ps_header));
    bzero(&ps_header,sizeof(struct netutil_ip_ps_header));

    p=is_udplite?136:17;

    udphdr.src_port=htons(sport);
    udphdr.dst_port=htons(dport);

    if(is_ipv6){
        memcpy(ps6_header.src_addr,saddr,16);
        memcpy(ps6_header.dst_addr,daddr,16);

        ps6_header.next_header=p;
        ps6_header.length=htons(length);
    }else{
        memcpy(ps_header.src_addr,saddr,4);
        memcpy(ps_header.dst_addr,daddr,4);

        ps_header.protocol=p;
        ps_header.length=htons(length);
    }

    if(is_udplite && csum_coverage<8){
        STDERR("wrong udplite csum_coverage value\r\n");
        return -1;
    }

    m=mbuf_get();
    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return -1;
    }

    if(is_udplite){
        udphdr.length=htons(length);
    }else{
        udphdr.csum_coverage=htons(csum_coverage);
    }



    return 0;
}