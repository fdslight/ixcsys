#include<string.h>

#include "passthrough.h"
#include "netif.h"
#include "../../../pywind/clib/debug.h"

static int passthrough_is_initialized=0;
static struct ixc_passthrough passthrough;
static struct ixc_mbuf *passthrough_tmp_mbuf=NULL;

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

    if(IXC_MBUF_FROM_LAN==m->from){
        hwaddr=m->src_hwaddr;
    }else{
        hwaddr=m->dst_hwaddr;
    }

    is_brd=hwaddr[0] & 0x01;
    
    // 源端地址的广播mac地址禁止通过
    if(is_brd && IXC_MBUF_FROM_LAN==m->from) return 0;

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
static void __ixc_passthrough_send_auto_from_lan(struct ixc_mbuf *m)
{
    // 直接发送流量到WAN网口
    m->netif=ixc_netif_get(IXC_NETIF_WAN);
    ixc_netif_send(m);
}

inline
static void __ixc_passthrough_send_for_brd(void *data)
{
    struct ixc_passthrough_node *node=data;
    struct ixc_ether_header *eth_header=NULL;

    struct ixc_mbuf *m=ixc_mbuf_clone(passthrough_tmp_mbuf);

    if(NULL==m){
        STDERR("no memory for malloc struct ixc_mbuf\r\n");
        return;
    }

    // 修改目标MAC地址头部,使其他机器收不到直通MAC广播
    eth_header=(struct ixc_ether_header *)(m->data+m->begin);
    memcpy(eth_header->dst_hwaddr,node->hwaddr,6);

    ixc_netif_send(m);
}

inline
static void __ixc_passthrough_send_auto_from_wan(struct ixc_mbuf *m)
{
    int is_brd;

    // 直接发送到LAN网口
    m->netif=ixc_netif_get(IXC_NETIF_LAN);
    is_brd=m->dst_hwaddr[0] & 0x01;

    // 非广播数据包直接发送
    if(!is_brd){
        ixc_netif_send(m);
        return;
    }

    passthrough_tmp_mbuf=m;
    map_each(passthrough.permit_map,__ixc_passthrough_send_for_brd);
    ixc_mbuf_put(m);
    passthrough_tmp_mbuf=NULL;
}

inline
void ixc_passthrough_send_auto(struct ixc_mbuf *m)
{
    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
        return;
    }

    if(IXC_MBUF_FROM_LAN==m->from) __ixc_passthrough_send_auto_from_lan(m);
    else __ixc_passthrough_send_auto_from_wan(m);
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

    return 0;
}

void ixc_passthrough_device_del(unsigned char *hwaddr)
{
    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
    }

    map_del(passthrough.permit_map,(char *)hwaddr,__ixc_passthrough_del_cb);
}