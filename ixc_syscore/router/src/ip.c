#include<arpa/inet.h>
#include<string.h>

#include "ip.h"
#include "ip6.h"
#include "netif.h"
#include "route.h"
#include "addr_map.h"
#include "ether.h"
#include "router.h"
#include "nat.h"
#include "ipunfrag.h"
#include "debug.h"
#include "global.h"
#include "npfwd.h"

#include "../../../pywind/clib/netutils.h"

static int ixc_ip_check_ok(struct ixc_mbuf *m,struct netutil_iphdr *header)
{
    int version=(header->ver_and_ihl & 0xf0) >> 4;
    unsigned short tot_len;
    unsigned char ipaddr_unspec[]=IXC_IPADDR_UNSPEC;

    if(m->tail-m->offset<28) return 0;
    if(4!=version) return 0;

    tot_len=ntohs(header->tot_len);

    if(tot_len > m->tail- m->offset) return 0;
    if(!memcmp(header->dst_addr,ipaddr_unspec,4)) return 0;
    if(header->dst_addr[0]==127) return 0;
    // 源地址与目的地址一样那么丢弃该数据包
    if(!memcmp(header->dst_addr,header->src_addr,4)){
        ixc_mbuf_put(m);
        return 0;
    }
    // 限制IP数据包最小长度
    if(tot_len<28) return 0;

    return 1;
}

static void ixc_ip_handle_from_wan(struct ixc_mbuf *m,struct netutil_iphdr *iphdr)
{
    struct netutil_udphdr *udphdr;
    struct ixc_netif *netif=m->netif;

    int hdr_len=(iphdr->ver_and_ihl & 0x0f) *4;
    unsigned short frag_info,frag_off;
    int mf;

    frag_info=ntohs(iphdr->frag_info);
    frag_off=frag_info & 0x1fff;
    mf=frag_info & 0x2000;
    
    // 检查是否是DHCP Client报文
    if(17==iphdr->protocol && frag_off==0){
        udphdr=(struct netutil_udphdr *)(m->data+m->offset+hdr_len);
        // 检查是DHCP client报文并且开启DHCP的那么处理DHCP报文
        if(ntohs(udphdr->dst_port)==68 && ntohs(udphdr->src_port)==67){
            //ixc_router_send(IXC_NETIF_WAN,0,IXC_FLAG_DHCP_CLIENT,m->data+m->begin,m->end-m->begin);
            //ixc_mbuf_put(m);
            ixc_npfwd_send_raw(m,17,IXC_FLAG_DHCP_CLIENT);
            return;
        }
    }
    // 注意这里的数据包检查要在DHCP报文之后
    // 没有设置IP地址那么就丢弃数据包
    if(!netif->isset_ip){
        ixc_mbuf_put(m);
        return;
    }

    //DBG("frag_off %d mf %d\r\n",frag_off,mf);
    // 如果IP数据包有分包那么首先合并数据包
    if(mf!=0 || frag_off!=0) m=ixc_ipunfrag_add(m);
    if(NULL==m) return;
    
    ixc_nat_handle(m);
}

static void ixc_ip_handle_from_lan(struct ixc_mbuf *m,struct netutil_iphdr *iphdr)
{
    struct netutil_udphdr *udphdr;
    int hdr_len=(iphdr->ver_and_ihl & 0x0f) *4;
    struct ixc_netif *netif=m->netif;

    if(!netif->isset_ip){
        ixc_mbuf_put(m);
        return;
    }

    // 检查是否是DHCP Server报文
    if(17==iphdr->protocol){
        udphdr=(struct netutil_udphdr *)(m->data+m->offset+hdr_len);
        // 检查是DHCP server报文并且开启DHCP的那么处理DHCP报文
        if(ntohs(udphdr->dst_port)==67 && ntohs(udphdr->src_port)==68){
            //ixc_router_send(IXC_NETIF_LAN,0,IXC_FLAG_DHCP_SERVER,m->data+m->begin,m->end-m->begin);
            //ixc_mbuf_put(m);
            ixc_npfwd_send_raw(m,17,IXC_FLAG_DHCP_SERVER);
            return;
        }
    }
    //DBG_FLAGS;
    // 如果网络关闭并且不是本机器发出的地址那么丢弃数据包
    if(!ixc_g_network_is_enabled() && memcmp(ixc_g_manage_addr_get(0),netif->ipaddr,4)){
        ixc_mbuf_put(m);
        return;
    }
    //DBG_FLAGS;
    // 发送数据到route
    ixc_route_handle(m);
}

void ixc_ip_handle(struct ixc_mbuf *mbuf)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(mbuf->data+mbuf->offset);
    unsigned short tot_len;
    struct ixc_netif *netif=mbuf->netif;
    
    if(!ixc_ip_check_ok(mbuf,header)){
        ixc_mbuf_put(mbuf);
        return;
    }

    tot_len=ntohs(header->tot_len);
    mbuf->is_ipv6=0;
    // 除去以太网的填充字节
    mbuf->tail=mbuf->offset+tot_len;

    if(IXC_NETIF_WAN==netif->type){
        ixc_ip_handle_from_wan(mbuf,header);
    }else{
        ixc_ip_handle_from_lan(mbuf,header);
    }
}

int ixc_ip_send(struct ixc_mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    int ip_ver= (header->ver_and_ihl & 0xf0) >> 4;
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);

    if(NULL==netif){
        ixc_mbuf_put(m);
        return -1;
    }

    if(!netif->isset_ip){
        ixc_mbuf_put(m);
        return -1;
    }

    // 检查IP版本是否符合要求
    if(4!=ip_ver && 6!=ip_ver){
        ixc_mbuf_put(m);
        return -1;
    }

    if(6==ip_ver) return ixc_ip6_send(m);

    // 丢弃多拨地址和保留地址
    if(header->dst_addr[0]>=224){
        ixc_mbuf_put(m);
        return -1;
    }
    m->is_ipv6=0;
    m->netif=netif;
    m->link_proto=0x0800;

    // 不是内网网段直接丢弃数据包
    if(!ixc_netif_is_subnet(m->netif,header->dst_addr,0,0)){
        ixc_mbuf_put(m);
        return -1;
    }

    // 直接发送
    memcpy(m->next_host,header->dst_addr,4);
    ixc_addr_map_handle(m);

    return 0;
}