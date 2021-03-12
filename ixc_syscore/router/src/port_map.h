#ifndef IXC_PORT_MAP_H
#define IXC_PORT_MAP_H

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/netutils.h"

struct ixc_port_map_record{
    unsigned char address[4];
    unsigned short port;
    unsigned char protocol;
};

struct ixc_port_map{
    struct map *m;
};

int ixc_port_map_init(void);
void ixc_port_map_uninit(void);

/// 增加映射记录
int ixc_port_map_add(unsigned char *address,unsigned char protocol,unsigned short port);
/// 删除映射记录
void ixc_port_map_del(unsigned char protocol,unsigned short port);
/// 检查记录是否存在
int ixc_port_map_add(unsigned char *address,unsigned char protocol,unsigned short port);

#endif