/*IPv6 地址NPTv6转换模块*/

#include "mbuf.h"

int ixc_nptv6_init(void);
void ixc_nptv6_uninit(void);

/// 是否开启IPv6前缀转换
int ixc_nptv6_set_enable(int enable);
void ixc_nptv6_handle(struct ixc_mbuf *m);


