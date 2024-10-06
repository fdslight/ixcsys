#include<string.h>

#include "passthrough.h"
#include "netif.h"
#include "route.h"

#include "../../../pywind/clib/debug.h"

static int passthrough_is_initialized=0;
static struct ixc_passthrough passthrough;

static void __ixc_passthrough_del_cb(void *data)
{
    struct ixc_passthrough_node *node=data;
    free(node);
}


int ixc_passthrough_init(void)
{
    struct map *m;
    int rs=map_new(&m,6);
    
    bzero(&passthrough,sizeof(struct ixc_passthrough));

    if(rs){
        STDERR("cannot init passthrough\r\n");
        return -1;
    }

    passthrough.permit_map=m;
    passthrough.count=0;
    passthrough_is_initialized=1;

    return 0;
}

void ixc_passthrough_uninit(void)
{
    passthrough_is_initialized=0;

    map_release(passthrough.permit_map,__ixc_passthrough_del_cb);
}

inline
int ixc_passthrough_is_passthrough_traffic(struct ixc_mbuf *m)
{
    unsigned char *hwaddr;
    int is_brd=0;
    char is_found=0;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
        return 0;
    }

    // 如果没有任何记录,那么不允许直通,主要针对广播报文
    if(0==passthrough.count) return 0;

    if(IXC_MBUF_FROM_LAN==m->from){
        hwaddr=m->src_hwaddr;
    }else{
        hwaddr=m->dst_hwaddr;
    }

    is_brd=hwaddr[0] & 0x01;
    
    // 源端地址的广播mac地址禁止通过
    if(is_brd && IXC_MBUF_FROM_LAN==m->from) return 0;

    // 当启用IPv6直通功能时禁用IPv6,与IPv6直通功能需要处理路由功能冲突
    if(m->link_proto==0x86dd && ixc_route_is_enabled_ipv6_pass()) return 0;

    // 检查MAC地址是否是多播或者广播地址
    if(!is_brd){
        map_find(passthrough.permit_map,(char *)hwaddr,&is_found);
        if(is_found) return 1;
        return 0;
    }

    // 多播和广播需要直通
    return 1;
}

inline
struct ixc_mbuf *ixc_passthrough_send_auto(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=NULL;
    struct ixc_mbuf *new_mbuf;
    int is_brd;
    unsigned char *hwaddr;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
        return NULL;
    }

    if(IXC_MBUF_FROM_LAN==m->from){
        hwaddr=m->src_hwaddr;
        netif=ixc_netif_get(IXC_NETIF_WAN);
    }else{
        hwaddr=m->dst_hwaddr;
        netif=ixc_netif_get(IXC_NETIF_LAN);
    }

    is_brd=hwaddr[0] & 0x01;

    if(is_brd && IXC_MBUF_FROM_WAN==m->from){
        new_mbuf=ixc_mbuf_clone(m);
    }else{
        new_mbuf=m;
        m=NULL;
    }

    new_mbuf->netif=netif;
    ixc_netif_send(new_mbuf);

    return m;
}

int ixc_passthrough_device_add(unsigned char *hwaddr)
{
    int rs;
    char is_found;
    struct ixc_passthrough_node *node;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
        return -1;
    }

    map_find(passthrough.permit_map,(char *)hwaddr,&is_found);
    if(is_found) return 0;

    node=malloc(sizeof(struct ixc_passthrough_node));
    if(NULL==node){
        STDERR("cannot malloc for struct ixc_passthrough_node\r\n");
        return -1;
    }

    memcpy(node->hwaddr,hwaddr,6);

    rs=map_add(passthrough.permit_map,(char *)hwaddr,node);

    if(rs){
        STDERR("cannot add passthrough device\r\n");
        free(node);
        return -1;
    }
    passthrough.count+=1;

    return 0;
}

void ixc_passthrough_device_del(unsigned char *hwaddr)
{
    char is_found;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
    }

    map_find(passthrough.permit_map,(char *)hwaddr,&is_found);

    if(is_found) passthrough.count-=1;

    map_del(passthrough.permit_map,(char *)hwaddr,__ixc_passthrough_del_cb);
}