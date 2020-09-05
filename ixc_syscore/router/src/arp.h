#ifndef IXC_ARP_H
#define IXC_ARP_H

#include "mbuf.h"

#pragma pack(push)
#pragma pack(1)

struct ixc_arp{
    unsigned short htype;
    unsigned short proto_type;
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

int ixc_arp_send(struct ixc_netif *netif,unsigned char *dst_hwaddr,unsigned char *dst_ipaddr,unsigned short op);
void ixc_arp_handle(struct ixc_mbuf *mbuf);

#endif