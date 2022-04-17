

#include<string.h>
#include<arpa/inet.h>

#include "../../../pywind/clib/netutils.h"

#include "vswitch.h"
#include "netif.h"
#include "ether.h"

static struct ixc_vsw vsw;
static int vsw_is_initialized=0;

int ixc_vsw_init(void)
{
    vsw_is_initialized=1;
    bzero(&vsw,sizeof(struct ixc_vsw));

    return 0;
}

void ixc_vsw_uninit(void)
{   
    vsw_is_initialized=0;
}

int ixc_vsw_enable(int enable,int is_ipv6)
{
    if(is_ipv6) vsw.ip6_enable=enable;
    else vsw.ip4_enable=enable;

    return 0;
}

int ixc_vsw_set_subnet(unsigned char *subnet,unsigned char prefix,int is_ipv6)
{
    unsigned char *msk=is_ipv6?vsw.ip6_mask:vsw.ip4_mask;
    unsigned char *res=is_ipv6?vsw.ip6_subnet:vsw.ip4_subnet;

    msk_calc(prefix,is_ipv6,msk);
    subnet_calc_with_prefix(subnet,prefix,is_ipv6,res);

    return 0;
}

inline
int ixc_vsw_is_from_subnet(unsigned char *address,int is_ipv6)
{
    unsigned char *subnet=NULL,*mask;

    if(is_ipv6){
        if(!vsw.ip6_enable) return 0;
        subnet=vsw.ip6_subnet;
        mask=vsw.ip6_mask;
    }else{
        if(!vsw.ip4_enable) return 0;
        subnet=vsw.ip4_subnet;
        mask=vsw.ip4_mask;
    }

    return is_same_subnet_with_msk(address,subnet,mask,is_ipv6);
}

void ixc_vsw_handle_from_user(struct ixc_mbuf *mbuf)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);
    struct ixc_ether_header *header;
    int size;
    unsigned short type;

    // 这里需要核对二层数据包是否正确
    // 检查数据包长度是否符合要求
    if(mbuf->end-mbuf->begin<15){
        ixc_mbuf_put(mbuf);
        return;
    }

    header=(struct ixc_ether_header *)(mbuf->data+mbuf->begin);
    type=ntohs(header->type);

    switch(type){
        // 限定支持以太网的IP,IPv6以及ARP协议
        case 0x0800:
        case 0x0806:
        case 0x86dd:
            break;
        default:
            ixc_mbuf_put(mbuf);
            return;
    }

    // 填充到60字节
    size=mbuf->end-mbuf->begin;
    if(size<60){
        bzero(mbuf->data+mbuf->end,60-size);
        mbuf->end+=(60-size);
    }

    // 把数据包发送到本地局域网
    mbuf->netif=netif;
    ixc_ether_send(mbuf,0);
}