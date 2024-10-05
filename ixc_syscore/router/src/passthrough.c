#include<string.h>

#include "passthrough.h"
#include "netif.h"
#include "../../../pywind/clib/debug.h"

static int passthrough_is_initialized=0;
static struct ixc_passthrough passthrough;

int ixc_passthrough_init(void)
{
    struct map *m;
    int rs=map_new(&m,6);
    
    bzero(&passthrough,sizeof(struct ixc_passthrough));

    if(rs){
        STDERR("cannot init passthrough");
        return -1;
    }

    passthrough.permit_map=m;
    passthrough_is_initialized=1;

    return 0;
}

void ixc_passthrough_uninit(void)
{
    passthrough_is_initialized=0;

    map_release(passthrough.permit_map,NULL);
}

inline
int ixc_passthrough_is_passthrough_traffic(struct ixc_mbuf *m)
{
    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough");
        return 0;
    }
    return 0;
}

inline
static void __ixc_passthrough_send_auto_from_lan(struct ixc_mbuf *m)
{
    // 直接发送流量到WAN网口
    m->netif=ixc_netif_get(IXC_NETIF_WAN);
    ixc_netif_send(m);
}

inline
static void __ixc_passthrough_send_auto_from_wan(struct ixc_mbuf *m)
{
    // 直接发送到LAN网口
    m->netif=ixc_netif_get(IXC_NETIF_LAN);
    ixc_netif_send(m);
}

inline
void ixc_passthrough_send_auto(struct ixc_mbuf *m)
{
    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough");
        return;
    }

    if(IXC_MBUF_FROM_LAN==m->from) __ixc_passthrough_send_auto_from_lan(m);
    else __ixc_passthrough_send_auto_from_wan(m);
}

int ixc_passthrough_device_add(unsigned char *hwaddr)
{
    int rs;
    char is_found;
    void *data;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough");
        return -1;
    }

    data=map_find(passthrough.permit_map,(char *)hwaddr,&is_found);
    if(is_found) return 0;

    rs=map_add(passthrough.permit_map,(char *)hwaddr,NULL);

    if(rs){
        STDERR("cannot add passthrough device");
        return -1;
    }

    return 0;
}

void ixc_passthrough_device_del(unsigned char *hwaddr)
{
    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough");
    }

    map_del(passthrough.permit_map,hwaddr,NULL);
}