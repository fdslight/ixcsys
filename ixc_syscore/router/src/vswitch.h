/** 虚拟交换 **/
#ifndef IXC_VSWITCH_H
#define IXC_VSWITCH_H

#include "mbuf.h"

#include "../../../pywind/clib/map.h"

/// 映射表超时时间
#define IXC_VSW_TABLE_TIMEOUT 600

struct ixc_vsw_record{
    unsigned char hwaddr[6];
    unsigned char pad;

#define IXC_VSW_FLG_LOCAL 0 //表示来自于本地网卡
#define IXC_VSW_FLG_FWD 1 // 表示需要重定向
    unsigned char flags;
};

/// 虚拟交换表
struct ixc_vsw_table{
    struct map *m;
};

int ixc_vsw_init(void);
void ixc_vsw_uninit(void);

/// 开启或者关闭虚拟交换
int ixc_vsw_enable(int enable);
/// 检查虚拟交换是否启用
int ixc_vsw_is_enabled(void);
struct ixc_mbuf *ixc_vsw_handle(struct ixc_mbuf *m);

#endif