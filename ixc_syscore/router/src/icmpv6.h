#ifndef IXC_ICMPv6_H
#define IXC_ICMPv6_H

#pragma pack(push)
#pragma pack(4)
/// 路由请求头部
struct ixc_icmpv6_rs_header{
    unsigned char type;
    unsigned char code;
    unsigned short checksum;
    char reserved[4];
};

/// 路由宣告头部
struct ixc_icmpv6_ra_header{
    unsigned char type;
    unsigned char code;
    unsigned short checksum;
    unsigned char cur_hop_limit;
    unsigned char m_o;
    unsigned short router_lifetime;
    unsigned int reachable_time;
    unsigned int retrans_timer;
};

/// 邻居请求格式
struct ixc_icmpv6_ns_header{
    unsigned char type;
    unsigned char code;
    unsigned short checksum;
    char reserved[4];
    unsigned char target_addr[16];
};

/// 邻居宣告格式
struct ixc_icmpv6_na_header{
    unsigned char type;
    unsigned char code;
    unsigned short checksum;
    unsigned int rso;
    unsigned char target_addr[16]; 
};

struct ixc_icmpv6_opt_prefix_info{
    unsigned char type;
    unsigned char length;
    unsigned char prefix_len;
    unsigned char la;
    unsigned int valid_lifetime;
    unsigned int preferred_lifetime;
    unsigned char reserved2[4];
    unsigned char prefix[16];
};

struct ixc_icmpv6_mtu{
    unsigned char type;
    unsigned char length;
    char reserved[2];
    unsigned int mtu;  
};

struct ixc_icmpv6_opt_link_addr{
    unsigned char type;
    unsigned char length;
    unsigned char hwaddr[6];
};

/// 路由宣告可选项
struct ixc_icmpv6_opt_ra{
    unsigned char type_hwaddr;
    unsigned char length_hwaddr;
    unsigned char hwaddr[6];
    unsigned char type_mtu;
    unsigned char length_mtu;
    unsigned char r1[2];
    unsigned int mtu;
    unsigned char type_prefix;
    unsigned char length_prefix;
    unsigned char prefix_length;
    unsigned char prefix_flags;
    unsigned int prefix_valid_lifetime;
    unsigned int prefix_preferred_lifetime;
    unsigned char r2[4];
    unsigned char prefix[16];
};

#pragma pack(pop)

#include "mbuf.h"
#include "netif.h"

#include "../../../pywind/clib/netutils.h"

int ixc_icmpv6_init(void);
void ixc_icmpv6_uninit(void);

void ixc_icmpv6_handle(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr);
/// 发送RA报文
// 如果hwaddr为空,那么自动生成all_nodes地址
int ixc_icmpv6_send_ra(unsigned char *hwaddr,unsigned char *ipaddr);
/// 发送路由器请求报文
int ixc_icmpv6_send_rs(void);
/// 发送邻居报文请求
int ixc_icmpv6_send_ns(struct ixc_netif *netif,unsigned char *src_ipaddr,unsigned char *dst_ipaddr);
/// 开启或者关闭ICMPv6 NDP代理,非0表示开启,0表示关闭
int ixc_icmpv6_ndp_proxy_enable(int status);
/// 是否已经开启了NDP代理
int ixc_icmpv6_is_enabled(void);

#endif