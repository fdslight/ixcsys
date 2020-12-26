
#include<sys/types.h>
#include<arpa/inet.h>
#include<string.h>

#include "udp.h"
#include "debug.h"
#include "mbuf.h"
#include "ip.h"
#include "ipv6.h"

#include "proxy_helper.h"

#include "../../../pywind/clib/netutils.h"

static void __udp_handle_v4(struct mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_udphdr *udphdr=NULL;
    struct netutil_ip_ps_header *ps_header;

    unsigned char protocol=header->protocol;
    int hdr_len=(header->ver_and_ihl & 0x0f) * 4,offset=0,is_udplite;
    unsigned char saddr[4],daddr[4];
    unsigned short sport,dport,csum;

    memcpy(saddr,header->src_addr,4);
    memcpy(daddr,header->dst_addr,4);

    m->offset+=hdr_len;
    offset=m->offset-12;

    udphdr=(struct netutil_udphdr *)(m->data+m->offset);

    // 检查UDP协议的检验和
    if(protocol==17){
        is_udplite=0;

        ps_header=(struct netutil_ip_ps_header *)(m->data+offset);
        
        memcpy(ps_header->src_addr,saddr,4);
        memcpy(ps_header->dst_addr,daddr,4);

        ps_header->pad[0]=0;
        ps_header->protocol=protocol;
        ps_header->length=udphdr->length;

        csum=csum_calc((unsigned short *)(m->data+offset),m->tail-offset);

        // 这段检验和检查有问题,代码需要重新修改
        if(csum!=0x0000){
            DBG("wrong UDP data packet checksum 0x%x\r\n",csum);
            mbuf_put(m);
            return;
        }
    }else{
        // 检查UDPLite的检验和
        is_udplite=1;
    }

    sport=ntohs(udphdr->src_port);
    dport=ntohs(udphdr->dst_port);

    netpkt_udp_recv(saddr,daddr,sport,dport,is_udplite,0,m->data+m->offset+8,m->tail-m->offset-8);
    mbuf_put(m);
}

static void __udp_handle_v6(struct mbuf *m)
{

}

void udp_handle(struct mbuf *m,int is_ipv6)
{
    if(is_ipv6) __udp_handle_v6(m);
    else __udp_handle_v4(m);
}

int udp_send(unsigned char *saddr,unsigned char *daddr,unsigned short sport,unsigned short dport,int is_udplite,int is_ipv6,unsigned short csum_coverage,void *data,size_t length)
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

    if(is_ipv6) ipv6_send(saddr,daddr,p,m->data+m->begin,m->end-m->begin);
    else ip_send(saddr,daddr,p,m->data+m->begin,m->end-m->begin);

    mbuf_put(m);

    return 0;
}