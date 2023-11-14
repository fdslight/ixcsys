#ifndef IXC_IPTV_H
#define IXC_IPTV_H

#include "mbuf.h"
// IPTV设备
struct ixc_iptv_dev{
    // 设备硬件地址
    unsigned char hwaddr[6];
    unsigned char pad[2];
};

int ixc_iptv_init(void);
void ixc_iptv_uninit(void);

// 启用或者关闭IPTV
int ixc_iptv_enable(int enable);

// 是否是IPTV设备的MAC地址
int ixc_iptv_is_iptv_device(const unsigned char *hwaddr);
// 处理IPTV数据包
void ixc_iptv_handle(struct ixc_mbuf *m);
// IPTV设备加入
int ixc_iptv_device_add(const unsigned char *hwaddr);
// IPTV设备删除
void ixc_iptv_device_del(const unsigned char *hwaddr);

#endif