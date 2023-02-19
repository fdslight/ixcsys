#ifndef IXC_ETHER_H
#define IXC_ETHER_H

#pragma pack(push)
#pragma pack(1)

struct ixc_ether_header{
    unsigned char dst_hwaddr[6];
    unsigned char src_hwaddr[6];
    union{
        unsigned short type;
        unsigned short length;
    };
};

#pragma pack(pop)

#endif