/* 指定地址直通,绕过路由器,注意此功能不同于路由里面的IPv6直通,路由里面的IPv6直通仍旧会计算路由 */
#ifndef IXC_PASSTHROUGH_H
#define IXC_PASSTHROUGH_H

#include "ether.h"
#include "mbuf.h"

#include "../../../pywind/clib/map.h"

/// 最多支持8台设备
#define IXC_PASSTHROUGH_DEV_MAX 8

struct ixc_passthrough_node;

struct ixc_passthrough{
    // 允许的映射HWADDR地址
    struct map *permit_map;
    struct ixc_passthrough_node *pass_nodes[IXC_PASSTHROUGH_DEV_MAX];
    unsigned int count;
    // 标记passdev过来的流量的VLAN ID,如果为0表示不标记
    unsigned short vlan_id_tagged_for_passdev;
};

struct ixc_passthrough_node{
    unsigned char hwaddr[6];
    //
    char index;
    char pad;
    // 是否是直通网卡
    int is_passdev;
};

int ixc_passthrough_init(void);
void ixc_passthrough_uninit(void);

/// @检查是否是直通流量
/// @param m 
/// @return 
int ixc_passthrough_is_passthrough_traffic(struct ixc_mbuf *m);

/// @智能发送流量到所有直通口
/// @param m 
/// @return 如果返回值为空那么不需要经过路由器内部协议栈处理,不为NULL那么继续处理
struct ixc_mbuf *ixc_passthrough_send_auto(struct ixc_mbuf *m);

/// @增加直通设备mac地址
/// @param hwaddr 
/// @return 
int ixc_passthrough_device_add(unsigned char *hwaddr,int is_passdev);

/// @删除直通设备地址
/// @param hwaddr 
void ixc_passthrough_device_del(unsigned char *hwaddr);

/// @处理来自于PASS网卡的报文
void ixc_passthrough_handle_from_passdev(struct ixc_mbuf *m);
/// @发送到PASS网卡
void ixc_passthrough_send2passdev(struct ixc_mbuf *m);
/// 是否是直通PASS的设备
int ixc_passthrough_is_passthrough2passdev_traffic(unsigned char *hwaddr);

/// 设置passdev穿透过来流量的VID
int ixc_passthrough_set_vid_for_passdev(unsigned short vid);

#endif
