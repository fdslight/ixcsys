#ifndef IXC_DHCP_SERVER_H
#define IXC_DHCP_SERVER_H


#include "../../../pywind/clib/map.h"

/// DHCP Server 会话
struct ixc_dhcp_server_record{

};

struct ixc_dhcp_server{
    struct map *record_map;
    // 服务器主机名
    char server_name[64];
    // 引导文件名
    char boot_filename[128];
};

#endif