#ifndef IXC_ARP_H
#define IXC_ARP_H

#pragma pack(push)
#pragma pack(1)

struct ixc_arp{
    unsigned char hwaddr_len;
    unsigned char protoaddr_len;
#define IXC_ARP_OP_REQ 1
#define IXC_ARP_OP_RESP 2
    unsigned short op;
    unsigned char src_hwaddr[6];
    unsigned char src_ipaddr[4];
    unsigned char dst_hwaddr[6];
    unsigned char dst_ipaddr[4];
};
#pragma pack(pop)

#endif