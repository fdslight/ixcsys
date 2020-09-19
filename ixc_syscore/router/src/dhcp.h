#ifndef IXC_DHCP_H
#define IXC_DHCP_H

#pragma pack(push)
#pragma pack(1)

struct ixc_dhcp{
    unsigned char op;
    unsigned char htype;
    unsigned char hlen;
    unsigned char hops;
    unsigned int xid;
    unsigned short secs;
    unsigned short flags;

    unsigned char ciaddr[4];
    unsigned char yiaddr[4];
    unsigned char siaddr[4];
    unsigned char giaddr[4];
    unsigned char chaddr[16];
    unsigned char sname[64];
    unsigned char file[128];
};

#pragma pack(pop)

enum{
    IXC_DHCP_DISCOVER=1,
    IXC_DHCP_OFFER,
    IXC_DHCP_REQUEST,
    IXC_DHCP_DECLINE,
    IXC_DHCP_ACK,
    IXC_DHCP_NAK,
    IXC_DHCP_RELEASE,
    IXC_DHCP_INFORM
};

#endif