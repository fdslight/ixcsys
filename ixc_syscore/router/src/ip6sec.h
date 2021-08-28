/** IPv6安全相关,用以提高IPv6安全性 **/
#ifndef IXC_IP6SEC_H
#define IXC_IP6SEC_H

#include<sys/types.h>

#include "mbuf.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/timer.h"

/// KEY大小
#define IXC_IP6SEC_KEYSIZE 32
/// 超时会话设置
#define IXC_IP6SEC_TIMEOUT 300

struct ixc_ip6sec{
    struct map *m;
    // 是否开启IPv6安全
    int enable;
};

struct ixc_ip6sec_info{
    struct time_data *tdata;
    time_t up_time;
    char key[IXC_IP6SEC_KEYSIZE];
};

int ixc_ip6sec_init(void);
void ixc_ip6sec_uninit(void);

/// IPv6安全检查
// 如果安全检查不通过,那么返回0,否则返回1
int ixc_ip6sec_check_ok(struct ixc_mbuf *m);

/// 开启或者关闭IPv6安全检查
int ixc_ip6sec_enable(int enable);

#endif