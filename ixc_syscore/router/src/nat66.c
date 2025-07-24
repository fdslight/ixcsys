
#include<string.h>

#include "nat66.h"

#include "../../../pywind/clib/netutils.h"

static struct ixc_nat66 nat66;

int ixc_nat66_init(void)
{
    bzero(&nat66,sizeof(struct ixc_nat66));

    return 0;
}

void ixc_nat66_uninit(void)
{

}

int ixc_nat66_enable(int enable)
{
    nat66.enable=enable;

    return 0;
}

int ixc_nat66_is_enabled(void)
{
    return nat66.enable;
}

int ixc_nat66_set_wan_prefix(unsigned char *lan_prefix,unsigned char *wan_prefix,unsigned char prefix_length)
{
    memcpy(nat66.lan_ip6subnet,lan_prefix,16);
    memcpy(nat66.wan_ip6subnet,wan_prefix,16);

    return 0;
}

static void ixc_nat66_for_icmpv6(struct ixc_mbuf *m,unsigned char *new_addr,int is_src)
{
    struct netutil_icmpv6hdr *icmpv6hdr=(struct netutil_icmpv6hdr *)(m->data+m->offset+40);
    struct netutil_ip6hdr *header=NULL;
    unsigned char *ptr=m->data+m->offset+48;
    int need_handle_flags=0;

    switch(icmpv6hdr->type){
        case 1:
        case 2:
        case 3:
        case 4:
            need_handle_flags=1;
            break;
        default:
            need_handle_flags=0;
            break;
    }
    // 只处理错误消息
    if(!need_handle_flags) return;
    // 重写错误消息内部的IPv6数据包
    header=(struct netutil_ip6hdr *)ptr;

    // 这里IPv6内部原始数据包需要反过来,因为是发送流量或者接收流量的复制
    if(is_src){
        rewrite_ip6_addr(header,new_addr,0);
    }else{
        rewrite_ip6_addr(header,new_addr,1);
    }
}

void ixc_nat66_prefix_modify(struct ixc_mbuf *m,int is_src)
{
    unsigned char *new_addr_ptr=is_src?nat66.wan_ip6subnet:nat66.lan_ip6subnet;
    unsigned char *modify_ptr;
    unsigned char new_addr[16];

    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);
    if(!nat66.enable) return;

    // 检查是否是需要改写的源地址
    if(is_src && memcmp(header->src_addr,nat66.lan_ip6subnet,8)) return;
    if(!is_src && memcmp(header->dst_addr,nat66.wan_ip6subnet,8)) return;

    modify_ptr=is_src?header->src_addr:header->dst_addr;

    memcpy(new_addr,new_addr_ptr,8);
    memcpy(new_addr+8,modify_ptr+8,8);

    rewrite_ip6_addr(header,new_addr,is_src);

    // 对ICMPv6进行特殊处理,以便支持错误机制
    if(58==header->next_header){
        ixc_nat66_for_icmpv6(m,new_addr,is_src);
    }
}