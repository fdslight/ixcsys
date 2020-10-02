

#include "natv6.h"

int ixc_natv6_init(void)
{
    return 0;
}

void ixc_natv6_uninit(void)
{

}

void ixc_natv6_handle(struct ixc_mbuf *m)
{
    ixc_mbuf_put(m);
}

int ixc_natv6_enable(int status,int type)
{
    return 0;
}