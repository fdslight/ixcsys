#include<arpa/inet.h>
#include<string.h>

#include "ether.h"
#include "arp.h"
#include "ip.h"
#include "ip6.h"
#include "netif.h"
#include "router.h"
#include "pppoe.h"
#include "route.h"
#include "traffic_log.h"
#include "passthrough.h"

#include "../../../pywind/clib/debug.h"

/// 是否开启以太网流量监控,如果开启那么将向指定的网卡发送一份出口数据
static int ether_net_monitor_enable=0;
/// 网络重定向硬件地址
static unsigned char ether_net_monitor_fwd_hwaddr[6];


/// 拷贝到监控主机
static void ixc_ether_copy_to_monitor_host(struct ixc_mbuf *mbuf)
{
    struct ixc_mbuf *m=ixc_mbuf_clone(mbuf);
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);
    struct ixc_ether_header *eth_header=NULL;

    if(NULL==m) return;

    eth_header=(struct ixc_ether_header *)(m->data+m->begin);

    // 修改网卡为内网网口
    m->netif=netif;
    // 修改目标mac地址
    memcpy(eth_header->dst_hwaddr,ether_net_monitor_fwd_hwaddr,6);
    // 发送数据
    ixc_netif_send(m);
}

// 以太网流量统计,所有统计针对LAN口
static void ixc_ether_traffic_statistics(struct ixc_mbuf *m,int dir)
{
    struct ixc_netif *netif=m->netif;
    struct ixc_ether_header *header=(struct ixc_ether_header *)(m->data+m->begin);

    if(IXC_NETIF_LAN!=netif->type) return;

    ixc_traffic_log_statistics(header,m->end-m->begin,dir);
}

int ixc_ether_send(struct ixc_mbuf *mbuf,int add_header)
{
    struct ixc_ether_header eth_header;
    struct ixc_netif *netif=mbuf->netif;
    int size;

    if(NULL==netif){
        STDERR("empty netif\r\n");
        ixc_mbuf_put(mbuf);
        return 0;
    }

    if(!add_header){
        ixc_ether_traffic_statistics(mbuf,IXC_TRAFFIC_LOG_DIR_IN);
        ixc_netif_send(mbuf);
        return 0;
    }

    // 首先屏蔽旧的头部
    mbuf->begin=mbuf->offset;

    memcpy(eth_header.dst_hwaddr,mbuf->dst_hwaddr,6);
    memcpy(eth_header.src_hwaddr,mbuf->src_hwaddr,6);

    eth_header.type=htons(mbuf->link_proto);

    mbuf->begin=mbuf->begin-sizeof(struct ixc_ether_header);

    memcpy(mbuf->data+mbuf->begin,&eth_header,sizeof(struct ixc_ether_header));

    size=mbuf->end-mbuf->begin;

    if(size<0){
        STDERR("size cannot is zero\r\n");
        ixc_mbuf_put(mbuf);
        return -1;
    }

    // 填充以太网以便满足60字节
    if(size<60){
        bzero(mbuf->data+mbuf->end,60-size);
        mbuf->end+=(60-size);
    }
    
    if(ether_net_monitor_enable && netif->type==IXC_NETIF_WAN){
        ixc_ether_copy_to_monitor_host(mbuf);
    }
    
    ixc_ether_traffic_statistics(mbuf,IXC_TRAFFIC_LOG_DIR_IN);
    ixc_netif_send(mbuf);

    return 0;
}

void ixc_ether_handle(struct ixc_mbuf *mbuf)
{
    struct ixc_ether_header *header;
    struct ixc_netif *netif=mbuf->netif;
    int length=mbuf->end-mbuf->begin;
    unsigned short type;
    
    // 检查长度是否合法,不合法直接丢包
    if(length<14){
        ixc_mbuf_put(mbuf);
        return;
    }
    
    //IXC_MBUF_LOOP_TRACE(mbuf);

    header=(struct ixc_ether_header *)(mbuf->data+mbuf->begin);
    type=ntohs(header->type);

    ixc_ether_traffic_statistics(mbuf,IXC_TRAFFIC_LOG_DIR_OUT);

    // 限定数据帧
    if(type < 0x0800){
        ixc_mbuf_put(mbuf);
        return;
    }
    
    // 源mac地址和目标mac地址一致丢弃数据包
    if(!memcmp(header->src_hwaddr,header->dst_hwaddr,6)){
        ixc_mbuf_put(mbuf);
        return;
    }

    memcpy(mbuf->dst_hwaddr,header->dst_hwaddr,6);
    memcpy(mbuf->src_hwaddr,header->src_hwaddr,6);

    mbuf->offset+=14;
    mbuf->link_proto=type;

    // 检查是否LAN的数据包是否需要直通PASS网卡
    if(IXC_NETIF_LAN==netif->type){
        if(ixc_passthrough_is_passthrough2passdev_traffic(mbuf->src_hwaddr)){
            ixc_passthrough_send2passdev(mbuf);
            return;
        }
    }

    if(IXC_NETIF_PASS==netif->type){
        ixc_passthrough_handle_from_passdev(mbuf);
        return;
    }
    
    // 检查是否需要直通到WAN口或者LAN口
    // 注意这段检查直通代码要在检查是否是自己MAC地址之前
    if(ixc_passthrough_is_passthrough_traffic(mbuf)){
        mbuf=ixc_passthrough_send_auto(mbuf);
        if(NULL==mbuf) return;
    }
    
    // 此处检查MAC地址是否是本地地址,非本地MAC地址丢弃数据包(前提是IPv6直通未开启)
    if(!ixc_ether_is_self(netif,header->dst_hwaddr)){
        if(type!=0x86dd){
            ixc_mbuf_put(mbuf);
            return;
        }
        if(!ixc_route_is_enabled_ipv6_pass()){
            ixc_mbuf_put(mbuf);
            return;
        }
    }
    
    if(ixc_pppoe_is_enabled() && IXC_NETIF_WAN==netif->type){
        // 如果WAN口开启PPPoE那么限制只支持PPPoE数据包
        if(type!=0x8864 && type!=0x8863){
            ixc_mbuf_put(mbuf);
            return;
        }
    }

    switch (type){
        // IP
        case 0x0800:
            ixc_ip_handle(mbuf);
            break;
        // ARP
        case 0x0806:
            ixc_arp_handle(mbuf);
            break;
        // IPv6
        case 0x86dd:
            ixc_ip6_handle(mbuf);
            break;
        // PPPoE discovery
        case 0x8863:
            if(IXC_NETIF_LAN==netif->type) ixc_mbuf_put(mbuf);
            else ixc_pppoe_handle(mbuf);
            break;
        // PPPoE session
        case 0x8864:
            if(IXC_NETIF_LAN==netif->type) ixc_mbuf_put(mbuf);
            else ixc_pppoe_handle(mbuf);
            break;
        default:
            ixc_mbuf_put(mbuf);
            break;
    }
}

int ixc_ether_send2(struct ixc_mbuf *m)
{
    struct ixc_ether_header *header;
    int size=0;

    if(NULL==m) return 0;
    
    if(NULL==m->netif){
        STDERR("empty netif\r\n");
        ixc_mbuf_put(m);
        return -1;
    }

    header=(struct ixc_ether_header *)(m->data+m->begin);
    m->link_proto=ntohs(header->type);

    size=m->end-m->begin;

    // 检查数据包是否合法
    if(size<13){
        ixc_mbuf_put(m);
        return -1;
    }

    if(ntohs(header->type)<0x0101){
        ixc_mbuf_put(m);
        return -1;
    }

    if(size<60){
        bzero(m->data+m->end,60-size);
        m->end+=(60-size);
    }

    if(ether_net_monitor_enable && m->netif->type==IXC_NETIF_WAN){
        ixc_ether_copy_to_monitor_host(m);
    }

    ixc_ether_traffic_statistics(m,IXC_TRAFFIC_LOG_DIR_IN);
    ixc_netif_send(m);

    return 0;
}

int ixc_ether_send3(struct ixc_mbuf *m,unsigned short tpid,unsigned short vlan_id)
{
    struct ixc_ether_vlan_header *header;
    int size;

    // TPID必须使用0x8100
    if(0x8100!=tpid){
        ixc_mbuf_put(m);
        return -1;
    }

    if(vlan_id<1 || vlan_id>4094){
        ixc_mbuf_put(m);
        return -2;
    }

    m->begin=m->offset=m->begin-sizeof(struct ixc_ether_vlan_header);

    header=(struct ixc_ether_vlan_header *)(m->data+m->begin);
    header->tpid=htons(tpid);
    header->vlan_info=htons(vlan_id);
    header->type=htons(m->link_proto);

    memcpy(header->dst_hwaddr,m->dst_hwaddr,6);
    memcpy(header->src_hwaddr,m->src_hwaddr,6);

    size=m->end-m->begin;
    if(size<60){
        bzero(m->data+m->end,60-size);
        m->end+=(60-size);
    }

    ixc_ether_send(m,0);

    return 0;
}

int ixc_ether_get_multi_hwaddr_by_ip(unsigned char *ip,unsigned char *result)
{
    result[0]=0x01;
    result[1]=0x00;
    result[2]=0x5e;
    result[3]=ip[1] & 0x7f;
    result[4]=ip[2];
    result[5]=ip[3];

    return 0;
}

int ixc_ether_get_multi_hwaddr_by_ipv6(unsigned char *ip6,unsigned char *result)
{
    result[0]=0x33;
    result[1]=0x33;

    memcpy(&result[2],ip6+12,4);

    return 0;
}

int ixc_ether_is_self(struct ixc_netif *netif,unsigned char *hwaddr)
{
    unsigned char all_zero[]={
        0x00,0x00,0x00,
        0x00,0x00,0x00
    };
    // 检查是否是多播地址
    if((hwaddr[0] & 0x01) == 1) return 1;
    if(!memcmp(all_zero,hwaddr,6)) return 1;
    if(!memcmp(hwaddr,netif->hwaddr,6)) return 1;
    
    return 0;
}

int ixc_ether_net_monitor_set(int enable,unsigned char *hwaddr)
{
    ether_net_monitor_enable=enable;
    if(NULL!=hwaddr) memcpy(ether_net_monitor_fwd_hwaddr,hwaddr,6);

    return 0;
}