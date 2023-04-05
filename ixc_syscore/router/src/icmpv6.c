#include<string.h>

#include "debug.h"
#include "icmpv6.h"
#include "mbuf.h"
#include "netif.h"
#include "ether.h"
#include "ip6.h"
#include "addr_map.h"
#include "route.h"

static int icmpv6_isset_dns=0;
static unsigned char icmpv6_dnsserver[16];
static unsigned char icmpv6_wan_dnsserver_a[16];
static unsigned char icmpv6_wan_dnsserver_b[16];

static int ixc_icmpv6_send(struct ixc_netif *netif,unsigned char *dst_hwaddr,unsigned char *src_ipaddr,unsigned char *dst_ipaddr,void *icmp_data,int length)
{
    struct ixc_mbuf *m=ixc_mbuf_get();
    struct netutil_icmpv6hdr *icmpv6_header=icmp_data;
    struct netutil_ip6_ps_header *ps_header;
    struct netutil_ip6hdr *ip6hdr;

    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        ixc_mbuf_put(m);
        return -1;
    }

    m->next=NULL;
    m->netif=netif;
    m->link_proto=0x86dd;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=IXC_MBUF_BEGIN;
    
    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memcpy(m->dst_hwaddr,dst_hwaddr,6);

    ip6hdr=(struct netutil_ip6hdr *)(m->data+m->offset-40);
    ps_header=(struct netutil_ip6_ps_header *)(m->data+m->offset-40);

    bzero(ps_header,40);

    memcpy(ps_header->src_addr,src_ipaddr,16);
    memcpy(ps_header->dst_addr,dst_ipaddr,16);

    ps_header->length=htonl(length);
    ps_header->next_header=58;

    memcpy(m->data+m->offset,icmp_data,length);

    icmpv6_header=(struct netutil_icmpv6hdr *)(m->data+m->offset);
    icmpv6_header->checksum=0;
    icmpv6_header->checksum=csum_calc((unsigned short *)(m->data+m->offset-40),length+40);

    IPv6_HEADER_SET(ip6hdr,0,0,length,58,255,src_ipaddr,dst_ipaddr);

    m->tail=m->offset+length;
    m->end=m->tail;

    m->offset=m->offset-40;
    m->begin=m->offset;

    ixc_ether_send(m,1);

    return 0;
}

static void ixc_icmpv6_handle_echo(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,struct netutil_icmpv6hdr *icmp_header)
{
    struct ixc_netif *netif=m->netif;
    struct netutil_icmpv6echo *echo=(struct netutil_icmpv6echo *)icmp_header,*reply_hdr;
    unsigned char buf[0xffff];

    if(icmp_header->code!=0){
        ixc_mbuf_put(m);
        return;
    }

    // 只处理echo请求
    if(icmp_header->type!=128){
        ixc_mbuf_put(m);
        return;
    }

    reply_hdr=(struct netutil_icmpv6echo *)buf;

    (reply_hdr->icmpv6hdr).type=129;
    (reply_hdr->icmpv6hdr).code=0;
    (reply_hdr->icmpv6hdr).checksum=0;
    reply_hdr->id=echo->id;
    reply_hdr->seq_num=echo->seq_num;

    memcpy(buf+8,m->data+m->offset+8,m->tail-m->offset-8);
    ixc_icmpv6_send(netif,m->src_hwaddr,iphdr->dst_addr,iphdr->src_addr,buf,m->tail-m->offset);

    ixc_mbuf_put(m);
}

/// 处理路由请求报文
static void ixc_icmpv6_handle_rs(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,unsigned char icmp_code)
{
    struct ixc_netif *netif=m->netif;
    struct ixc_icmpv6_opt_link_addr *opt;
    unsigned char ip6addr_all_routers[]=IXC_IP6ADDR_ALL_ROUTERS;

    if(netif->type==IXC_NETIF_WAN || icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }

    if(m->tail-m->offset!=16){
        ixc_mbuf_put(m);
        return;
    }

    // 目标地址必须是所有的路由器
    if(memcmp(iphdr->dst_addr,ip6addr_all_routers,16)){
        ixc_mbuf_put(m);
        return;
    }

    opt=(struct ixc_icmpv6_opt_link_addr *)(m->data+m->offset+8);

    if(!netif->isset_ip6){
        ixc_mbuf_put(m);
        return;
    }
    
    ixc_icmpv6_send_ra(opt->hwaddr,iphdr->src_addr);
    ixc_mbuf_put(m);
}

/// 处理路由宣告报文
static void ixc_icmpv6_handle_ra(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,unsigned char icmp_code)
{
    struct ixc_netif *netif=m->netif;
    //struct ixc_icmpv6_ra_header *ra_header;
    struct ixc_icmpv6_opt_prefix_info *opt_prefix=NULL;

    unsigned char *ptr;
    unsigned char type,length;
    int is_err=0,A=0,v,size=0;
    unsigned char gw_hwaddr[6],byte,slaac_addr[16];
    //unsigned char unspec_addr[]=IXC_IP6ADDR_UNSPEC;
    unsigned int mtu=netif->mtu_v6;

    v=(m->tail-m->offset)/8;

    if(0!=v){
        ixc_mbuf_put(m);
        return;
    }

    if(netif->type==IXC_NETIF_LAN || icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }

    //ra_header=(struct ixc_icmpv6_ra_header *)(m->data+m->offset);
    ptr=m->data+m->offset+16;

    while(size<(m->end-m->offset-16)){
        type=ptr[0];
        length=ptr[1];
        
        if(length==1 && (type!=1 || type!=5)){
            is_err=1;
            break;
        }

        if(type==3 && length!=4){
            is_err=1;
            break;
        }

        if(type==25 && length<3){
            is_err=1;
            break;
        }

        switch(type){
            case 1:
                memcpy(gw_hwaddr,ptr+2,6);
                break;
            case 3:
                opt_prefix=(struct ixc_icmpv6_opt_prefix_info *)ptr;
                break;
            case 5:
                mtu=ntohl(*((unsigned int *)(ptr+2)));
                break;
        }

        size+=length*8;
        ptr+=length * 8;
    }

    if(is_err){
        ixc_mbuf_put(m);
        return;
    }

    if(NULL==opt_prefix){
        ixc_mbuf_put(m);
        return;
    }

    byte=opt_prefix->prefix[0];

    // 首先检查地址是否合法
    if(byte==0x00 || byte==0xff || byte==0xfe){
        ixc_mbuf_put(m);
        return;
    }

    // 检查前缀是否符合无状态地址配置要求
    if(opt_prefix->prefix_len>64 || opt_prefix->prefix_len < 48){
        STDERR("cannot apply to stateless address set because of RA prefix is %d\r\n",opt_prefix->prefix_len);
        ixc_mbuf_put(m);
        return;
    }

    // 检查上级路由器是否允许无状态地址配置
    A=opt_prefix->la & 0x40;
    if(!A){
        STDERR("cannot apply to stateless address set because of RA not permit %d\r\n",opt_prefix->prefix_len);
        ixc_mbuf_put(m);
        return;
    }

    if(mtu>1500){
        STDERR("Wrong MTU value from RA%u\r\n",mtu);
        ixc_mbuf_put(m);
        return;
    }

    memcpy(slaac_addr,opt_prefix->prefix,opt_prefix->length);
    
    ixc_ip6_eui64_get(netif->hwaddr,slaac_addr);
    // 为LAN和WAN各分配一个IP地址
    // 为WAN分配地址
    ixc_netif_set_ip(IXC_NETIF_WAN,slaac_addr,64,1);
    // 此处发送邻居请求,检查地址是否冲突
    //ixc_icmpv6_send_ns(netif,unspec_addr,slaac_addr);

    // 为LAN分配一个地址
    //if_lan=ixc_netif_get(IXC_NETIF_LAN);
    //ixc_ip6_eui64_get(if_lan->hwaddr,slaac_addr);
    //ixc_netif_set_ip(IXC_NETIF_LAN,slaac_addr,64,1);

    netif->mtu_v6=mtu;
    memcpy(netif->ip6_default_router_hwaddr,gw_hwaddr,6);

    ixc_mbuf_put(m);
}

/// 处理邻居请求报文
static void ixc_icmpv6_handle_ns(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,unsigned char icmp_code)
{
    struct ixc_netif *netif=m->netif;
    struct ixc_icmpv6_ns_header *ns_hdr=NULL;
    struct ixc_icmpv6_opt_link_addr *ns_opt,*na_opt;
    struct ixc_icmpv6_na_header *na_header;

    unsigned char *ptr,unspec_addr[]=IXC_IP6ADDR_UNSPEC;

    unsigned char buf[32];
    unsigned int rso=0;
    int flags=0,is_unspec_addr=0,size=32;
    unsigned char dst_hwaddr[6];
    unsigned char dst_ipaddr[]=IXC_IP6ADDR_ALL_NODES;

    //DBG_FLAGS;
    if(icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }

    //DBG_FLAGS;
    // 如果是邻居冲突检测那么ICMPv6应该是24字节
    if(!memcmp(unspec_addr,iphdr->src_addr,16)) {
        is_unspec_addr=1;
        size=24;
    }

    //DBG("%d %d %d %d\r\n",m->begin,m->offset,m->tail,m->end);
    if(m->tail-m->offset!=size){
        ixc_mbuf_put(m);
        return;
    }
    
    //DBG_FLAGS;
    ns_hdr=(struct ixc_icmpv6_ns_header *)(m->data+m->offset);
    ns_opt=(struct ixc_icmpv6_opt_link_addr *)(m->data+m->offset+24);

    if(!memcmp(ns_hdr->target_addr,netif->ip6_local_link_addr,16)){
        flags=1;
        ptr=netif->ip6_local_link_addr;
    }

    //DBG_FLAGS;
    if(!memcmp(ns_hdr->target_addr,netif->ip6addr,16)){
        flags=1;
        ptr=netif->ip6addr;
    }

    if(!flags){
        ixc_mbuf_put(m);
        return;
    }
    //DBG_FLAGS;
    bzero(buf,32);

    na_header=(struct ixc_icmpv6_na_header *)buf;
    na_opt=(struct ixc_icmpv6_opt_link_addr *)(&buf[24]);

    if(!is_unspec_addr) {
        memcpy(dst_ipaddr,iphdr->src_addr,16);
        memcpy(dst_hwaddr,ns_opt->hwaddr,6);
    }else{
        ixc_ether_get_multi_hwaddr_by_ipv6(dst_ipaddr,dst_hwaddr);
    }

    if(netif->type==IXC_NETIF_LAN){
        rso=rso | (0x00000001 << 31);
    }
    rso=rso | (0x00000001<<30);
    rso=rso | (0x00000001<<29);
    na_header->type=136;
    na_header->code=0;
    na_header->rso=htonl(rso);

    memcpy(na_header->target_addr,ptr,16);

    // 非冲突检测的处理方式
    if(!is_unspec_addr){
        na_opt->type=2;
        na_opt->length=1;
        memcpy(na_opt->hwaddr,netif->hwaddr,6);
    }

    //char addr[128];
    //inet_ntop(AF_INET6,iphdr->src_addr,addr,128);
    //DBG("from:%s %x:%x:%x:%x\r\n",addr,ns_opt->hwaddr[0],ns_opt->hwaddr[1],ns_opt->hwaddr[2],ns_opt->hwaddr[3]);

    ixc_icmpv6_send(netif,dst_hwaddr,ptr,dst_ipaddr,buf,size);
    ixc_mbuf_put(m);
}

/// 处理邻居宣告报文
static void ixc_icmpv6_handle_na(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr,unsigned char icmp_code)
{
    struct ixc_netif *netif=m->netif;
    struct ixc_icmpv6_na_header *na_header;
    struct ixc_icmpv6_opt_link_addr *opt;
    struct ixc_addr_map_record *r;
    //unsigned char all_nodes[]=IXC_IP6ADDR_ALL_NODES;

    int rs;

    //DBG_FLAGS;

    if(icmp_code!=0){
        ixc_mbuf_put(m);
        return;
    }
    if(m->tail-m->offset!=32){
        ixc_mbuf_put(m);
        return;
    }

    na_header=(struct ixc_icmpv6_na_header *)(m->data+m->offset);
    opt=(struct ixc_icmpv6_opt_link_addr *)(m->data+m->offset+24);

    if(opt->type!=2 || opt->length!=1){
        ixc_mbuf_put(m);
        return;
    }
    r=ixc_addr_map_get(na_header->target_addr,1);
    if(r){
        // 如果不一致那么修改
        if(memcmp(r->hwaddr,opt->hwaddr,6)) memcpy(r->hwaddr,opt->hwaddr,6);
        
        ixc_mbuf_put(m);
        r->up_time=time(NULL);
        r->is_changed=0;
        return;
    }

    rs=ixc_addr_map_add(netif,na_header->target_addr,opt->hwaddr,1);
    if(rs<0){
        ixc_mbuf_put(m);
        STDERR("cannot add address map for IPv6\r\n");
        return;
    }

    ixc_mbuf_put(m);
}

int ixc_icmpv6_init(void)
{
    bzero(icmpv6_dnsserver,16);
    bzero(icmpv6_wan_dnsserver_a,16);
    bzero(icmpv6_wan_dnsserver_b,16);

    icmpv6_isset_dns=0;

    return 0;
}

void ixc_icmpv6_uninit(void)
{

}

void ixc_icmpv6_handle(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr)
{
    struct ixc_netif *netif=m->netif;
    struct netutil_icmpv6hdr *icmp_header;

    icmp_header=(struct netutil_icmpv6hdr *)(m->data+m->offset+40);
    // 指向到ICMP头部
    m->offset+=40;

    if(icmp_header->type==128 || icmp_header->type==129){
        // 不是发往本级的ICMP echo数据包直接丢弃
        if(memcmp(iphdr->dst_addr,netif->ip6_local_link_addr,16) && memcmp(iphdr->dst_addr,netif->ip6addr,16)){
            ixc_mbuf_put(m);
            return;
        }
        ixc_icmpv6_handle_echo(m,iphdr,icmp_header);
        return;
    }

    // 检查格式是否正确
    if(iphdr->hop_limit!=255){
        ixc_mbuf_put(m);
        return;
    }

    switch(icmp_header->type){
        case 133:
            ixc_icmpv6_handle_rs(m,iphdr,icmp_header->code);
            break;
        case 134:
            ixc_icmpv6_handle_ra(m,iphdr,icmp_header->code);
            break;
        case 135:
            ixc_icmpv6_handle_ns(m,iphdr,icmp_header->code);
            break;
        case 136:
            ixc_icmpv6_handle_na(m,iphdr,icmp_header->code);
            break;
        default:
            ixc_mbuf_put(m);
            break;
    }
}

int ixc_icmpv6_send_ra(unsigned char *hwaddr,unsigned char *ipaddr)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);
    struct ixc_icmpv6_ra_header *ra_header;
    struct ixc_icmpv6_opt_ra *ra_opt;
    unsigned char dst_ipaddr[]=IXC_IP6ADDR_ALL_NODES;
    unsigned char dst_hwaddr[6];
    struct ixc_icmpv6_opt_dns opt_dns;
    int size=64;

    unsigned char buf[256];
    
    bzero(buf,256);
    bzero(&opt_dns,sizeof(struct ixc_icmpv6_opt_dns));

    ra_header=(struct ixc_icmpv6_ra_header *)buf;
    ra_opt=(struct ixc_icmpv6_opt_ra *)(&buf[16]);

    ra_header->type=134;
    ra_header->code=0;
    ra_header->checksum=0;
    ra_header->cur_hop_limit=0;
    ra_header->router_lifetime=htons(1800);

    ra_opt->type_hwaddr=1;
    ra_opt->length_hwaddr=1;
    memcpy(ra_opt->hwaddr,netif->hwaddr,6);

    ra_opt->type_mtu=5;
    ra_opt->length_mtu=1;
    ra_opt->mtu=htonl(1280);

    ra_opt->type_prefix=3;
    ra_opt->length_prefix=4;
    ra_opt->prefix_length=64;
    ra_opt->prefix_flags=0xc0;
    ra_opt->prefix_valid_lifetime=0xffffffff;
    ra_opt->prefix_preferred_lifetime=0xffffffff;
    
    memcpy(ra_opt->prefix,netif->ip6_subnet,16);

    if(NULL==hwaddr){
        ixc_ether_get_multi_hwaddr_by_ipv6(dst_ipaddr,dst_hwaddr);
    }else{
        memcpy(dst_hwaddr,hwaddr,6);
        memcpy(dst_ipaddr,ipaddr,16);
    }

    // 增加DNS下发
    if(icmpv6_isset_dns){
        opt_dns.type=25;
        opt_dns.length=3;
        memcpy(opt_dns.dnsserver,icmpv6_dnsserver,16);
        
        memcpy(((char *)(ra_opt))+size,&opt_dns,sizeof(struct ixc_icmpv6_opt_dns));
        size+=sizeof(struct ixc_icmpv6_opt_dns);
    }
    
    ixc_icmpv6_send(netif,dst_hwaddr,netif->ip6_local_link_addr,dst_ipaddr,buf,size);

    return 0;
}

int ixc_icmpv6_send_rs(void)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    struct ixc_icmpv6_rs_header *icmp_header;
    struct ixc_icmpv6_opt_link_addr *opt;

    unsigned char all_routers[]=IXC_IP6ADDR_ALL_ROUTERS;
    unsigned char dst_hwaddr[6];
    unsigned char buf[16];

    if(NULL==netif){
        STDERR("cannot get WAN network card\r\n");
        return -1;
    }
    bzero(buf,16);

    icmp_header=(struct ixc_icmpv6_rs_header *)buf;
    opt=(struct ixc_icmpv6_opt_link_addr *)(&buf[8]);

    icmp_header->type=133;
    icmp_header->code=0;
    icmp_header->checksum=0;

    opt->type=1;
    opt->length=1;

    memcpy(opt->hwaddr,netif->hwaddr,6);

    ixc_ether_get_multi_hwaddr_by_ipv6(all_routers,dst_hwaddr);
    ixc_icmpv6_send(netif,dst_hwaddr,netif->ip6_local_link_addr,all_routers,buf,16);

    //DBG_FLAGS;

    return 0;
}

int ixc_icmpv6_send_ns(struct ixc_netif *netif,unsigned char *src_ipaddr,unsigned char *dst_ipaddr)
{
    struct ixc_icmpv6_opt_link_addr *opt;
    struct ixc_icmpv6_ns_header *ns_header;

    unsigned char sol_addr[]=IXC_IP6ADDR_SOL_NODE_MULTI;
    unsigned char dst_hwaddr[16];

    unsigned char buf[32];

    bzero(buf,32);

    ns_header=(struct ixc_icmpv6_ns_header *)buf;
    opt=(struct ixc_icmpv6_opt_link_addr *)(&buf[24]);

    ns_header->type=135;
    ns_header->code=0;
    ns_header->checksum=0;

    memcpy(ns_header->target_addr,dst_ipaddr,16);

    opt->type=1;
    opt->length=1;

    memcpy(opt->hwaddr,netif->hwaddr,6);
    memcpy(&sol_addr[13],&dst_ipaddr[13],3);

    ixc_ether_get_multi_hwaddr_by_ipv6(dst_ipaddr,dst_hwaddr);

    return ixc_icmpv6_send(netif,dst_hwaddr,src_ipaddr,sol_addr,buf,32);
}

void ixc_icmpv6_send_error_msg(struct ixc_netif *netif,unsigned char *dst_hwaddr,unsigned char *daddr,unsigned char type,unsigned char code,unsigned int pad_data,void *data,unsigned short data_size)
{
    unsigned char buf[0xffff];
    struct netutil_icmpv6hdr *icmpv6_header=(struct netutil_icmpv6hdr *)buf;

    if(data_size>1200) data_size=1200;

    icmpv6_header->type=type;
    icmpv6_header->code=code;
    icmpv6_header->checksum=0;

    memcpy(buf+4,&pad_data,4);
    memcpy(buf+8,data,data_size);

    ixc_icmpv6_send(netif,dst_hwaddr,netif->ip6addr,daddr,buf,data_size+8);
}

void ixc_icmpv6_filter_and_modify(struct ixc_mbuf *m)
{
    struct netutil_icmpv6hdr *icmp_header;
    struct ixc_icmpv6_opt_dns *opt_dns;
    struct netutil_ip6hdr *ip6_header;
    struct netutil_ip6_ps_header *ps_header;

    unsigned buf[0x20000];

    unsigned char *ptr;
    unsigned char type,length;
    int offset=56,size=0,x;

    ip6_header=(struct netutil_ip6hdr *)(m->data+m->offset);
    icmp_header=(struct netutil_icmpv6hdr *)(m->data+m->offset+40);

    // 不是ICMPv6 RA报文直接pass
    if(icmp_header->type!=134) return;
    
    ptr=((unsigned char *)(icmp_header))+16;
    memcpy(buf+40,icmp_header,16);

    while(size<(m->end-m->offset-40-16)){
        type=ptr[0];
        length=ptr[1];
        x=length * 8;

        switch(type){
            case 25:
                if(length>=3){
                    memcpy(icmpv6_wan_dnsserver_a,ptr+8,16);
                    if(length>=4) memcpy(icmpv6_wan_dnsserver_b,ptr+24,16);
                }
                break;
            default:
                memcpy(buf+offset,ptr,length);
                offset+=x;
                break;
        }
        size+=x;
        ptr+=x;
    }

    if(icmpv6_isset_dns){
        opt_dns=(struct ixc_icmpv6_opt_dns *)(buf+offset);
        bzero(opt_dns,24);
        opt_dns->type=25;
        opt_dns->length=3;
        opt_dns->lifetime=htonl(1800);

        memcpy(opt_dns->dnsserver,icmpv6_dnsserver,16);
        offset+=24;
    }
    
    ps_header=(struct netutil_ip6_ps_header *)(buf);
    bzero(ps_header,40);

    memcpy(ps_header->src_addr,ip6_header->src_addr,16);
    memcpy(ps_header->dst_addr,ip6_header->dst_addr,16);

    ps_header->length=htonl(offset-40);
    ps_header->next_header=58;

    icmp_header=(struct netutil_icmpv6hdr *)(buf+40);
    icmp_header->checksum=0;
    icmp_header->checksum=csum_calc((unsigned short *)(buf),offset);

    IPv6_HEADER_SET(ip6_header,0,0,offset-40,58,64,ps_header->src_addr,ps_header->dst_addr);

    memcpy(m->data+m->offset+40,buf+40,offset-40);

    m->tail=m->offset+offset;
    m->end=m->tail;
}

int ixc_icmpv6_dns_set(unsigned char *dnsserver)
{
    if(NULL==dnsserver) return -1;
    memcpy(icmpv6_dnsserver,dnsserver,16);

    icmpv6_isset_dns=1;

    return 0;
}

void ixc_icmpv6_dns_unset(void)
{
    icmpv6_isset_dns=0;
}

int ixc_icmpv6_wan_dnsserver_get(unsigned char *dns_a,unsigned char *dns_b)
{
    memcpy(dns_a,icmpv6_wan_dnsserver_a,16);
    memcpy(dns_b,icmpv6_wan_dnsserver_b,16);

    return 0;
}