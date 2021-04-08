#include<string.h>

#include "icmp.h"
#include "ip.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/debug.h"

void ixc_icmp_handle_self(struct ixc_mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    int hdr_len= (header->ver_and_ihl & 0x0f) * 4;
    struct netutil_icmphdr *icmphdr=(struct netutil_icmphdr *)(m->data+m->offset+hdr_len);
    unsigned char src_ipaddr[4],dst_ipaddr[4];
    unsigned short csum;

    // 只处理echo请求
    if(8!=icmphdr->type && 0!=icmphdr->code){
        ixc_mbuf_put(m);
        return;
    }

    memcpy(src_ipaddr,header->dst_addr,4);
    memcpy(dst_ipaddr,header->src_addr,4);

    rewrite_ip_addr(header,src_ipaddr,1);
    rewrite_ip_addr(header,dst_ipaddr,0);

    csum=csum_calc_incre(icmphdr->type,0,icmphdr->checksum);
    icmphdr->checksum=csum;
    icmphdr->type=0;

    ixc_ip_send(m);
}

void ixc_icmp_send(unsigned char *saddr,unsigned char *daddr,struct netutil_icmphdr *icmphdr,void *data,unsigned short data_size)
{
    struct ixc_mbuf *m=NULL;
    struct netutil_iphdr *header;
    unsigned short csum;
    struct netutil_icmphdr *icmphdr2;
    unsigned char *s;

    if(data_size>1400){
        STDERR("icmp packet is too large\r\n");
        return;
    }

    m=ixc_mbuf_get();

    if(NULL==m){
        STDERR("cannot get mbuf for icmp send\r\n");
        return;
    }

    m->begin=IXC_MBUF_BEGIN;
    m->offset=IXC_MBUF_BEGIN;

    srand (time(NULL));

    // 此处初始化头部
    header=(struct netutil_iphdr *)(m->data+m->offset);

    bzero(header,20);

    header->ver_and_ihl=0x45;
    header->tos=0;
    header->tot_len=htons(data_size+20);
    header->id= rand() & 0xffff;
    header->frag_info=0;
    header->ttl=64;
    header->protocol=1;
    
    memcpy(header->dst_addr,daddr,4);
    memcpy(header->src_addr,saddr,4);

    csum=csum_calc((unsigned short *)header,20);

    header->checksum=csum;

    icmphdr2=(struct netutil_icmphdr *)(m->data+m->offset+20);

    memcpy(icmphdr2,icmphdr,8);
    memcpy(m->data+m->offset+28,data,data_size);

    // 非偶数字节填充一个值为0的字节,以便计算校验和
    if(data_size%2!=0){
        s=m->data+m->offset+28+data_size+1;
        *s='\0';
    }

    icmphdr2->checksum=0;
    csum=csum_calc((unsigned short *)icmphdr2,8);
    icmphdr2->checksum=csum;

    m->tail=m->offset+28+data_size;
    m->end=m->tail;

    DBG("%d\r\n",m->end-m->begin);

    ixc_ip_send(m);
}

void ixc_icmp_send_time_ex_msg(unsigned char *saddr,unsigned char *daddr,unsigned char code,void *data,unsigned short data_size)
{
    unsigned char buf[8];
    struct netutil_icmphdr *icmphdr=(struct netutil_icmphdr *)buf;
    bzero(buf,8);

    icmphdr->type=11;
    icmphdr->code=code;

    ixc_icmp_send(saddr,daddr,icmphdr,data,data_size);
}
