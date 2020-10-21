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

#endif