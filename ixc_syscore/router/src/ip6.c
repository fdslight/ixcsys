
#include<string.h>
#include<time.h>

#include "ip.h"
#include "ip6.h"
#include "icmpv6.h"
#include "netif.h"
#include "debug.h"
#include "pppoe.h"
#include "route.h"
#include "addr_map.h"
#include "global.h"
#include "sec_net.h"
#include "router.h"
#include "npfwd.h"
#include "qos.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"

static struct sysloop *ip6_sysloop=NULL;
static time_t ip6_up_time=0;
static int ip6_enable_no_system_dns_drop=0;
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

    ip6_up_time=time(NULL);

    if(!ixc_route_is_enabled_ipv6_pass()){
        ixc_icmpv6_send_rs();
        if(netif->isset_ip6){
            ixc_icmpv6_send_ra(NULL,NULL);
        }
    }
    // 如果设置了IPv6那么定时发送RA
    //if(!ixc_route_is_enabled_ipv6_pass() && netif->isset_ip6) ixc_icmpv6_send_ra(NULL,NULL);
}

static int ixc_ip6_check_ok(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header;
    unsigned short payload_len;
    int ver;
    //unsigned char ip6_unspec_addr[]=IXC_IP6ADDR_UNSPEC;
    //unsigned char ip6_loopback_addr[]=IXC_IP6ADDR_LOOPBACK;

    if(m->tail-m->offset<48) return 0;

    header=(struct netutil_ip6hdr *)(m->data+m->offset);
    // 原地址与目标地址一致那么丢弃数据包
    if(!memcmp(header->src_addr,header->dst_addr,16)) return 0;
    ver=(header->ver_and_tc & 0xf0) >>4;
    if(ver!=6) return 0;

    payload_len=ntohs(header->payload_len);
    if(m->tail-m->offset < (payload_len+40)) return 0;
    // 限制最大长度
    if(payload_len > 1460) return 0;
    //if(!memcmp(ip6_loopback_addr,header->dst_addr,16) || !memcmp(ip6_unspec_addr,header->dst_addr,16)) return 0;

    return 1;
}

static int ixc_ip6_is_dhcp(struct ixc_mbuf *m,struct netutil_ip6hdr *header)
{
    struct netutil_udphdr *udp_header;

    if(17!=header->next_header) return 0;
    //if((header->dst_addr[0] >> 4)!=0x0f) return 0;

    udp_header=(struct netutil_udphdr *)(m->data+m->offset+40);
    // DHCP服务端
    if(ntohs(udp_header->dst_port)==547 && ntohs(udp_header->src_port)==546) return 2;
    // DHCP客户端
    if(ntohs(udp_header->dst_port)==546 && ntohs(udp_header->src_port)==547) return 1;

    return 0;
}

static void ixc_ip6_handle_from_wan(struct ixc_mbuf *m,struct netutil_ip6hdr *header)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    // 服务端响应DHCPv6服务数据包
    if(ixc_ip6_is_dhcp(m,header)==1 && !ixc_route_is_enabled_ipv6_pass()){
        ixc_npfwd_send_raw(m,17,IXC_FLAG_DHCP_CLIENT);
        return;
    }

    // 检查是否开启了隧道功能
    if(!ixc_ip_4in6_is_enabled()){
        ixc_qos_add(m);
        return;
    }
    
    // 如果不是接口地址直接执行下一步
    if(memcmp(netif->ip6addr,header->dst_addr,16)){
        ixc_qos_add(m);
        return;
    }

    // 检查源端地址是否是隧道地址
    if(memcmp(header->src_addr,ixc_ip_4in6_peer_address_get(),16)){
        ixc_qos_add(m);
        return;
    }

    // 检查是否是4in6封装
    if(0x04!=header->next_header){
        ixc_qos_add(m);
        return;
    }
    
    // 屏蔽IPv6头部
    m->offset=m->offset+40;
    m->begin=m->offset;

    //ixc_route_handle(m);
    //ixc_qos_add(m);
    ixc_ip_handle(m);
}

/// @是否是系统DNS请求
/// @param header 
/// @return 如果是非系统请求,返回1,否则返回0
static int ixc_ip6_is_no_system_dns_req(struct ixc_mbuf *m,struct netutil_ip6hdr *header)
{
    unsigned char *g_manage_addr=ixc_g_manage_addr_get(1);
    struct netutil_udphdr *udphdr;
    unsigned short dst_port;
    // 检查地址是否符合要求
    if(!memcmp(header->src_addr,g_manage_addr,16)) return 0;
    // 检查协议是否符合要求
    switch(header->next_header){
        case 6:
        case 17:
            break;
        default:
            return 0;
    }
    
    // 因为TCP和UDP头部端口位置布局一样,因此直接用UDP定义
    udphdr=(struct netutil_udphdr *)(m->data+m->offset+40);
    
    dst_port=ntohs(udphdr->dst_port);
    // 检查是否是53和853端口
    if(dst_port!=53 && dst_port!=853) return 0;

    return 1;
}

static void ixc_ip6_handle_from_lan(struct ixc_mbuf *m,struct netutil_ip6hdr *header)
{
    if(!ixc_g_network_is_enabled()){
        ixc_mbuf_put(m);
        return;
    }

    // 如果访问DHCPv6 server并且是直通状态那么丢弃dhcp请求数据包
    if(ixc_ip6_is_dhcp(m,header)==2 && ixc_route_is_enabled_ipv6_pass()){
        ixc_mbuf_put(m);
        return;
    }

    // 如果开启非系统DNS丢弃并且是非系统DNS请求,那么丢弃数据包
    if(ip6_enable_no_system_dns_drop && ixc_ip6_is_no_system_dns_req(m,header)){
        ixc_mbuf_put(m);
        return;
    }

    if(ixc_route_is_enabled_ipv6_pass()) ixc_addr_map_add(m->netif,header->src_addr,m->src_hwaddr,1);

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
    ip6_enable_no_system_dns_drop=0;
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
    /*if(!ixc_route_is_enabled_ipv6_pass() && !ixc_pppoe_is_enabled()){
        ixc_mbuf_put(mbuf);
        return;
    }*/

    //DBG_FLAGS;
    if(!ixc_ip6_check_ok(mbuf)){
        ixc_router_report_wrong_ippkt(mbuf->src_hwaddr,mbuf->dst_hwaddr,"Wrong IPv6 packet");
        //DBG_FLAGS;
        ixc_mbuf_put(mbuf);
        return;
    }

    header=(struct netutil_ip6hdr *)(mbuf->data+mbuf->offset);
    // IPv6的长度不包含固定头部,这里需要加上头部
    mbuf->end=mbuf->tail=mbuf->offset+ntohs(header->payload_len)+40;
    mbuf->is_ipv6=1;

    //DBG_FLAGS;
    //ixc_addr_map_check(header->src_addr,mbuf->src_hwaddr,1);

    if(IXC_NETIF_WAN==netif->type){
        //DBG_FLAGS;
        ixc_ip6_handle_from_wan(mbuf,header);
    }else{
        ixc_ip6_handle_from_lan(mbuf,header);
    }
}

int ixc_ip6_send(struct ixc_mbuf *mbuf)
{
    struct netutil_ip6hdr *header;
    // 强制为LAN网卡
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);

    if(NULL==netif){
        ixc_mbuf_put(mbuf);
        return -1;
    }

    if(!netif->isset_ip6 && !ixc_route_is_enabled_ipv6_pass()){
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
    if(!ixc_netif_is_subnet(netif,header->dst_addr,1,0) && !ixc_route_is_enabled_ipv6_pass()){
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

int ixc_ip6_no_system_dns_drop_enable(int enable)
{
    ip6_enable_no_system_dns_drop=enable;
    return 0;
}

int ixc_ip6_send_to_peer_for_4in6(struct ixc_mbuf *m,unsigned char *peer_address)
{
    struct netutil_ip6hdr *header=NULL;
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);

    if(NULL==netif){
        ixc_mbuf_put(m);
        STDERR("cannot get wan netif\r\n");
        return -1;
    }

    m->is_ipv6=1;
    m->netif=netif;
    m->offset=m->offset-40;
    m->begin=m->offset;

    header=(struct netutil_ip6hdr *)(m->data+m->offset);
    header->ver_and_tc=0x60;
    // 这里固定流标签
    header->flow_label[0]=0x00;
    header->flow_label[1]=0x00;
    header->flow_label[2]=0x00;
    // 出去IPv6头部
    header->payload_len=htons(m->end-m->begin-40);
    header->next_header=0x04;
    header->hop_limit=128;
    
    memcpy(header->src_addr,netif->ip6addr,16);
    memcpy(header->dst_addr,peer_address,16);

    ixc_ip6_handle_from_lan(m,header);

    return 0;
}