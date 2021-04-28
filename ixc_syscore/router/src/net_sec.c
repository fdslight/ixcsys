
#include<string.h>

#include "sec_net.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/timer.h"

static struct ixc_sec_net sec_net;
static int sec_net_is_initialized=0;

int ixc_sec_net_init(void)
{
    bzero(&sec_net,sizeof(struct ixc_sec_net));




    return 0;
}

void ixc_sec_net_uninit(void)
{
    sec_net_is_initialized=0;
}

int ixc_sec_net_src_rule_add(unsigned char *hwaddr,unsigned char *address,short action,int is_ipv6)
{
    return 0;
}

int ixc_sec_net_src_rule_del(unsigned char *hwaddr,unsigned char *address,int is_ipv6)
{
    return 0;
}