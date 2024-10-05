/* 指定地址直通,绕过路由器,注意此功能不同于路由里面的IPv6直通,路由里面的IPv6直通仍旧会计算路由 */
#ifndef IXC_PASSTHROUGH_H
#define IXC_PASSTHROUGH_H

#include "ether.h"
#include "mbuf.h"

#include "../../../pywind/clib/map.h"

struct ixc_passthrough{
    // 允许的映射HWADDR地址
    struct map *permit_map;
};

int ixc_passthrough_init(void);
void ixc_passthrough_uninit(void);

/// @检查是否是直通流量
/// @param m 
/// @return 
int ixc_passthrough_is_passthrough_traffic(struct ixc_mbuf *m);

/// @智能发送流量到所有直通口
/// @param m 
void ixc_passthrough_send_auto(struct ixc_mbuf *m);

/// @增加直通设备mac地址
/// @param hwaddr 
/// @return 
int ixc_passthrough_device_add(unsigned char *hwaddr);

/// @删除直通设备地址
/// @param hwaddr 
void ixc_passthrough_device_del(unsigned char *hwaddr);


#endif
