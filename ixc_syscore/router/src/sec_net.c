
#include<string.h>

#include "sec_net.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/timer.h"

static struct ixc_sec_net sec_net;
static int sec_net_is_initialized=0;

int ixc_sec_net_init(void)
{
    struct map *m=NULL;
    int rs;

    bzero(&sec_net,sizeof(struct ixc_sec_net));

    rs=map_new(&m,6);
    if(0!=rs){
        STDERR("cannot create map for log hwaddr\r\n");
        return -1;
    }

    sec_net.log_hwaddr=m;


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