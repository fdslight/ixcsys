

#include "route.h"

#include "../../../pywind/clib/debug.h"

int ixc_route_init(void)
{
    return 0;
}

void ixc_route_uninit(void)
{

}

int ixc_route_add(unsigned char *subnet,unsigned char prefix,int is_ipv6,int is_linked)
{
    return 0;
}

void ixc_route_del(unsigned char *ip,int is_ipv6)
{

}

struct ixc_route_info *ixc_route_find(unsigned char *ip,int is_ipv6)
{
    return NULL;
}

void ixc_route_handle(struct ixc_mbuf *m,int is_ipv6)
{
    ixc_mbuf_put(m);
}