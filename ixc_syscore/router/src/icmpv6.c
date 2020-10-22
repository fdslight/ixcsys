#include "icmpv6.h"

int ixc_icmpv6_init(void)
{
    return 0;
}

void ixc_icmpv6_uninit(void)
{
    return;
}

void ixc_icmpv6_handle(struct ixc_mbuf *m)
{
    ixc_mbuf_put(m);
}