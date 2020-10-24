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
    unsigned int rso[4];
    unsigned char target_addr[16]; 
};

struct ixc_icmpv6_prefix_info{
    unsigned char type;
    unsigned char length;
    unsigned char prefix_len;
    unsigned char la;
    unsigned int valid_lifetime;
    unsigned int preferred_lifetime;
    unsigned char reserved2[4];
};

struct ixc_icmpv6_mtu{
    unsigned char type;
    unsigned char length;
    char reserved[2];
    unsigned int mtu;  
};

#pragma pack(pop)

/// 所有的路由器地址
#define IXC_ICMPv6_ALL_ROUTERS_ADDR {0xff,0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x02}
/// 所有的节点地址
#define IXC_ICMPv6_ALL_NODES_ADDR {0xff,0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01}

#include "mbuf.h"
#include "../../../pywind/clib/netutils.h"

void ixc_icmpv6_handle(struct ixc_mbuf *m,struct netutil_ip6hdr *iphdr);

/// 发送RA报文
int ixc_icmpv6_send_ra(void);
/// 发送路由器请求报文
int ixc_icmpv6_send_rs(void);

#endif