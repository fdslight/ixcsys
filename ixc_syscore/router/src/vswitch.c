

#include "vswitch.h"
#include "debug.h"

int ixc_vsw_init(void)
{
    return 0;
}

void ixc_vsw_uninit(void)
{

}

/// 开启或者关闭虚拟交换
int ixc_vsw_enable(int enable)
{
    return 0;
}

/// 检查虚拟交换是否启用
int ixc_vsw_is_enabled(void)
{
    return 0;
}

struct ixc_mbuf *ixc_vsw_handle(struct ixc_mbuf *m)
{
    return NULL;
}