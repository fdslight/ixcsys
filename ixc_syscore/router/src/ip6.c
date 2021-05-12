
#include<string.h>
#include<time.h>

#include "ip6.h"
#include "icmpv6.h"
#include "netif.h"
#include "debug.h"
#include "pppoe.h"
#include "route.h"
#include "addr_map.h"
#include "global.h"
#include "sec_net.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"

static struct sysloop *ip6_sysloop=NULL;
static time_t ip6_up_time=0;
static int ip6_is_initialized=0;

static void ixc_ip6_sysloop_cb(struct sysloop *loop)
{
    time_t now_time=time(NULL);
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);

    if(now_time-ip6_up_time<60) return;

    /// 如果PPPoE没有开启那么发送ICMPv6 RS报文
    /**if(!ixc_pppoe_is_enabled()){
        ixc_icmpv6_send_rs();
    }**/
    
    // LAN口设置了IPv6地址那么发布路由宣告
    if(netif->isset_ip6) ixc_icmpv6_send_ra(NULL,NULL);

    ip6_up_time=time(NULL);
}

static int ixc_ip6_check_ok(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header;
    int ver;
    //unsigned char ip6_unspec_addr[]=IXC_IP6ADDR_UNSPEC;
    //unsigned char ip6_loopback_addr[]=IXC_IP6ADDR_LOOPBACK;

    if(m->tail-m->offset<48) return 0;

    header=(struct netutil_ip6hdr *)(m->data+m->offset);
    // 原地址与目标地址一致那么丢弃数据包
    if(!memcmp(header->src_addr,header->dst_addr,16)) return 0;
    ver=(header->ver_and_tc & 0xf0) >>4;
    if(ver!=6) return 0;

    //if(!memcmp(ip6_loopback_addr,header->dst_addr,16) || !memcmp(ip6_unspec_addr,header->dst_addr,16)) return 0;

    return 1;
}

static void ixc_ip6_handle_from_wan(struct ixc_mbuf *m,struct netutil_ip6hdr *header)
{
    ixc_route_handle(m);
}

static void ixc_ip6_handle_from_lan(struct ixc_mbuf *m,struct netutil_ip6hdr *header)
{
    if(!ixc_g_network_is_enabled()){
        ixc_mbuf_put(m);
        return;
    }

    ixc_sec_net_handle_from_lan(m);
    //ixc_route_handle(m);
}

int ixc_ip6_init(void)
{

    ip6_sysloop=sysloop_add(ixc_ip6_sysloop_cb,NULL);

    if(NULL==ip6_sysloop){
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }
    ip6_up_time=time(NULL);

    ip6_is_initialized=1;

    return 0;
}

void ixc_ip6_uninit(void)
{
    if(!ip6_is_initialized) return;

    sysloop_del(ip6_sysloop);
}

void ixc_ip6_handle(struct ixc_mbuf *mbuf)
{
    struct netutil_ip6hdr *header;
    struct ixc_netif *netif=mbuf->netif;

    // 未启用IPv6地址并且未开启IPv6穿透那么丢弃数据包
    if(!netif->isset_ip6 && !ixc_route_is_enabled_ipv6_pass()){
        ixc_mbuf_put(mbuf);
        return;
    }

    if(!ixc_ip6_check_ok(mbuf)){
        ixc_mbuf_put(mbuf);
        return;
    }

    header=(struct netutil_ip6hdr *)(mbuf->data+mbuf->offset);
    mbuf->end=mbuf->tail=mbuf->offset+ntohs(header->payload_len);
    mbuf->is_ipv6=1;

    ixc_addr_map_check(header->src_addr,mbuf->src_hwaddr,1);

    if(IXC_NETIF_WAN==netif->type){
        ixc_ip6_handle_from_wan(mbuf,header);
    }else{
        ixc_ip6_handle_from_lan(mbuf,header);
    }
}

int ixc_ip6_send(struct ixc_mbuf *mbuf)
{
    struct netutil_ip6hdr *header;
    // 强制为LAN网卡
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);;

    if(NULL==netif){
        ixc_mbuf_put(mbuf);
        return -1;
    }

    if(!netif->isset_ip6){
        ixc_mbuf_put(mbuf);
        return -1;
    }

    if(!ixc_ip6_check_ok(mbuf)){
        ixc_mbuf_put(mbuf);
        return -1;
    }

    header=(struct netutil_ip6hdr *)(mbuf->data+mbuf->offset);
    mbuf->is_ipv6=1;
    mbuf->netif=netif;
    mbuf->link_proto=0x86dd;
    mbuf->from=IXC_MBUF_FROM_APP;

    // 和LAN网口地址不在同一个网段那么丢弃数据包
    if(!ixc_netif_is_subnet(netif,header->dst_addr,1,0)){
        ixc_mbuf_put(mbuf);
        return -1;
    }
   
    memcpy(mbuf->next_host,header->dst_addr,16);
 
    ixc_addr_map_handle(mbuf);

    return 0;
}

int ixc_ip6_eui64_get(unsigned char *hwaddr,unsigned char *result)
{
    unsigned char x;

    result[0]=hwaddr[0];
    result[1]=hwaddr[1];
    result[2]=hwaddr[2];
    result[3]=0xff;
    result[4]=0xfe;
    result[5]=hwaddr[3];
    result[6]=hwaddr[4];
    result[7]=hwaddr[5];

    x=result[0] & 0x02;

    if(x) result[0]=result[0] & 0xfd;
    else result[0]=result[0] & 0xff;

    return 0;
}

int ixc_ip6_local_link_get(unsigned char *hwaddr,unsigned char *result)
{
    memset(result,0x00,16);

    result[0]=0xfe;
    result[1]=0x80;

    ixc_ip6_eui64_get(hwaddr,&result[8]);
    
    return 0;
}

int ixc_ip6_addr_get(unsigned char *hwaddr,unsigned char *subnet,unsigned char *result)
{
    memcpy(result,subnet,16);
    ixc_ip6_eui64_get(hwaddr,&result[8]);

    return 0;
}