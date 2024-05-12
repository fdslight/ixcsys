#include<string.h>

#include "global.h"

static unsigned char manage_addr[4];
static unsigned char manage_addr6[16];
static int g_network_enable=1;
static unsigned char ip6_passthrough_router_hwaddr[6];

int ixc_g_init(void)
{
    bzero(manage_addr,4);
    bzero(manage_addr6,16);
    bzero(ip6_passthrough_router_hwaddr,6);

    return 0;
}

void ixc_g_uninit(void)
{

}

inline
void *ixc_g_manage_addr_get(int is_ipv6)
{
    if(is_ipv6) return manage_addr6;
    else return manage_addr;
}

int ixc_g_manage_addr_set(unsigned char *addr,int is_ipv6)
{
    if(is_ipv6) memcpy(manage_addr6,addr,16);
    else memcpy(manage_addr,addr,4);

    return 0;
}

int ixc_g_network_enable(int enable)
{
    g_network_enable=enable;
    return 0;
}

inline
int ixc_g_network_is_enabled(void)
{
    return g_network_enable;
}

inline
int ixc_g_ip6_pass_router_hwaddr_set(unsigned char *hwaddr)
{
    memcpy(ip6_passthrough_router_hwaddr,hwaddr,6);
    
    return 0;
}

inline
unsigned char *ixc_g_ip6_pass_router_hwaddr_get(void)
{
    return ip6_passthrough_router_hwaddr;
}