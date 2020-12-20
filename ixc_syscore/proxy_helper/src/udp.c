
#include<sys/types.h>
#include<arpa/inet.h>
#include<string.h>

#include "udp.h"
#include "debug.h"
#include "mbuf.h"
#include "ip.h"
#include "ipv6.h"

#include "../../../pywind/clib/netutils.h"

int udp_send(unsigned char *saddr,unsigned char *daddr,unsigned short sport,unsigned short dport,int is_ipv6,int is_udplite,unsigned short csum_coverage,void *data,size_t length)
{
    struct netutil_udphdr *udphdr;
    struct netutil_ip6_ps_header *ps6_header;
    struct netutil_ip_ps_header *ps_header;
    struct mbuf *m=NULL;
    unsigned char p;
    unsigned short csum;
    int offset;
    
    p=is_udplite?136:17;

    if(is_udplite && csum_coverage<8){
        STDERR("wrong udplite csum_coverage value\r\n");
        return -1;
    }

    m=mbuf_get();
    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return -1;
    }

    m->begin=MBUF_BEGIN;
    m->offset=m->begin;
    m->tail=length+8;
    m->end=m->tail;

    udphdr=(struct netutil_udphdr *)(m->data+m->offset);
    bzero(udphdr,sizeof(struct netutil_udphdr));

    udphdr->src_port=htons(sport);
    udphdr->dst_port=htons(dport);

    if(is_udplite) udphdr->csum_coverage=htons(csum_coverage);
    else udphdr->length=htons(length+8);

    if(is_ipv6){
        offset=m->begin-40;
        ps6_header=(struct netutil_ip6_ps_header *)(m->data+offset);

        bzero(ps6_header,40);

        memcpy(ps6_header->src_addr,saddr,16);
        memcpy(ps6_header->dst_addr,daddr,16);

        ps6_header->next_header=p;
        ps6_header->length=htons(length+8);
    }else{
        offset=m->begin-12;
        ps_header=(struct netutil_ip_ps_header *)(m->data+offset);

        bzero(ps_header,12);

        memcpy(ps_header->src_addr,saddr,4);
        memcpy(ps_header->dst_addr,daddr,4);

        ps_header->protocol=p;
        ps_header->length=htons(length+8);
    }

    memcpy(m->data+m->offset+8,data,length);

    if(is_udplite) csum=csum_calc((unsigned short *)(m->data+m->offset),csum_coverage);
    else csum=csum_calc((unsigned short *)(m->data+m->offset),m->end-offset);
    
    udphdr->checksum=htons(csum);
    m->begin=m->offset=offset;

    if(is_ipv6) return ipv6_send(saddr,daddr,p,m);
    else return ip_send(saddr,daddr,p,m);
}