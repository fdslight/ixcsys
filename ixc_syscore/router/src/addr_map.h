#ifndef IXC_ADDR_MAP_H
#define IXC_ADDR_MAP_H

#include<time.h>

#include "../../../pywind/clib/map.h"

struct ixc_addr_map{
    struct map *ip_record;
    struct map *ip6_record;
};

struct ixc_addr_map_record{
    unsigned char address[16];
    time_t up_time;
    unsigned char hwaddr[6];
};

#endif