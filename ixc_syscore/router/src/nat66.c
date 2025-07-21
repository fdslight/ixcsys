
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
}