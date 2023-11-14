
#include<string.h>

#include "iptv.h"
#include "ether.h"

#include "../../../pywind/clib/map.h"

static struct map *iptv_devices=NULL;
static int iptv_enable=0;

static void __ixc_iptv_dev_del_fn(void *data)
{
    struct ixc_iptv_dev *dev=data;
    free(dev);
}

int ixc_iptv_init(void)
{
    int rs=map_new(&iptv_devices,6);

    if(rs){
        STDERR("cannot create map for IPTV\r\n");
        return -1;
    }
    iptv_enable=0;

    return 0;
}

void ixc_iptv_uninit(void)
{
    map_release(iptv_devices,__ixc_iptv_dev_del_fn);
}

int ixc_iptv_enable(int enable)
{
    iptv_enable=enable;
    return 0;
}

// 是否是IPTV设备的MAC地址
int ixc_iptv_is_iptv_device(const unsigned char *hwaddr)
{
    char is_found;
    struct ixc_iptv_dev *dev;
    
    if(!iptv_enable) return 0;

    dev=map_find(iptv_devices,(char *)hwaddr,&is_found);

    if(NULL==dev) return 0;

    return 1;
}

static void __ixc_iptv_handle_from_iptv_if(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);
    // 修改为LAN口
    m->netif=netif;
    // 直通直接发送给LAN网口
    ixc_ether_send2(m);
    //ixc_mbuf_put(m);
}

// 处理IPTV数据包
void ixc_iptv_handle(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;

    // 未开启IPTV那么丢弃IPTV数据包
    if(!iptv_enable){
        ixc_mbuf_put(m);
        return;
    }

    // 如果是IPTV网口收到的数据包进行处理
    if(IXC_NETIF_IPTV==netif->type){
        __ixc_iptv_handle_from_iptv_if(m);
        return;
    }
    
    netif=ixc_netif_get(IXC_NETIF_IPTV);
    m->netif=netif;

    ixc_ether_send2(m);
}


int ixc_iptv_device_add(const unsigned char *hwaddr)
{
    struct ixc_iptv_dev *dev=NULL;
    int is_err;

    if(ixc_iptv_is_iptv_device(hwaddr)) return 0;

    dev=malloc(sizeof(struct ixc_iptv_dev));
    if(NULL==dev){
        STDERR("cannot malloc IPTV device memory\r\n");
        return -1;
    }
    bzero(dev,sizeof(struct ixc_iptv_dev));

    is_err=map_add(iptv_devices,(char *)hwaddr,dev);
    
    if(is_err){
        STDERR("cannot add IPTV device\r\n");
        free(dev);
        return -1;
    }

    return 0;
}


void ixc_iptv_device_del(const unsigned char *hwaddr)
{
    if(!ixc_iptv_is_iptv_device(hwaddr)) return;
    
    map_del(iptv_devices,(char *)hwaddr,__ixc_iptv_dev_del_fn);
}