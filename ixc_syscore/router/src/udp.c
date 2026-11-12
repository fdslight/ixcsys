#include<stdlib.h>
#include<string.h>

#include "udp.h"
#include "debug.h"

#include "../../../pywind/clib/netutils.h"

struct ixc_mbuf *ixc_udp_build_pkts(struct ixc_mbuf *mdata,int data_size,\
const unsigned char *dest_addr,const unsigned char *src_addr,int is_ipv6,\
unsigned short dest_port,unsigned short src_port,\
unsigned short mtu,int is_udplite,unsigned short udplite_csum_coverage)
{

    unsigned char protocol=is_udplite?136:17;
    unsigned short csum=0,length;
    unsigned char *s=NULL;
    unsigned char *user_data=mdata->data+mdata->begin;
    int data_len=mdata->end-mdata->begin;
    int size=0;

    struct netutil_ip_ps_header *ps_header=NULL;
    struct netutil_ip6_ps_header *ps6_header=NULL;
    struct netutil_udphdr *udphdr=(struct netutil_udphdr *)(user_data-8);

    if(mtu>9000){
        STDERR("Wrong MTU value %d\r\n,the sizeof max is 9000",mtu);
        ixc_mbuf_put(mdata);
        return NULL;
    }

    if(is_ipv6 && mtu < 1280){
        STDERR("Wrong MTU value %d for IPv6,the size of min is 1280\r\n",mtu);
        ixc_mbuf_put(mdata);
        return NULL;
    }

    if(is_ipv6 && mtu < 1280){
        STDERR("Wrong MTU value %d for IPv6,the size of min is 1280\r\n",mtu);
        ixc_mbuf_put(mdata);
        return NULL;
    }

    if(!is_ipv6 && mtu < 576){
        STDERR("Wrong MTU value %d for IPv4,the size of min is 576\r\n",mtu);
        ixc_mbuf_put(mdata);
        return NULL;
    }

    length=htons(data_len+8);
    if(is_ipv6) {
        ps6_header=(struct netutil_ip6_ps_header *)(user_data-48);
        memcpy(ps6_header->src_addr,src_addr,16);
        memcpy(ps6_header->dst_addr,dest_addr,16);

        bzero(ps6_header->pad,3);

        ps6_header->length=htonl(length+8);
        ps6_header->next_header=protocol;
    }else {
        ps_header=(struct netutil_ip_ps_header *)(user_data-20);
    
        memcpy(ps_header->src_addr,src_addr,4);
        memcpy(ps_header->dst_addr,dest_addr,4);

        ps_header->pad[0]=0;
        ps_header->length=htons(data_len+8);
    }
    
    if(is_udplite){
        if(udplite_csum_coverage<8) udplite_csum_coverage=8;
        if(data_len+8<udplite_csum_coverage) udplite_csum_coverage=data_len+8;
        udphdr->csum_coverage=htons(udplite_csum_coverage);
        csum=csum_calc((unsigned short *)(udphdr),udplite_csum_coverage);
    }else{
        s=user_data-8;
        csum=csum_calc((unsigned short *)s,size+8+data_len);
    }
    udphdr->checksum=htons(csum);

    // 执行头部偏移
    mdata->begin=mdata->begin-8;
    mdata->offset=mdata->begin;

    data_len=mdata->end-mdata->begin;

    if(is_ipv6){
        size=mtu-48;
    }else{
        size=mtu-28;
    }

    // 此处构建IP头部

    return mdata;
}