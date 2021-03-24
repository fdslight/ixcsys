#include<string.h>

#include "global.h"

static unsigned char manage_addr[4];
static unsigned char manage_addr6[16];

int ixc_g_init(void)
{
    bzero(manage_addr,4);
    bzero(manage_addr6,16);

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