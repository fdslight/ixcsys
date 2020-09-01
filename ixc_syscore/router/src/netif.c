#include<stdio.h>
#include<stdlib.h>
#include<errno.h>
#include<string.h>
#include<fcntl.h>
#include<unistd.h>

#include "netif.h"
#include "router.h"
#include "ether.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netif/tuntap.h"
#include "../../../pywind/clib/netif/hwinfo.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_netif netif_objs[IXC_NETIF_MAX];
static int netif_is_initialized=0;

int ixc_netif_init(void)
{
    bzero(&netif_objs,sizeof(struct ixc_netif)*IXC_NETIF_MAX);

    netif_is_initialized=1;

    return 0;
}

void ixc_netif_uninit(void)
{
    if(!netif_is_initialized) return;

    for(int n=0;n<IXC_NETIF_MAX;n++){
        if(netif_objs[n].is_used){
            ixc_netif_delete(n);
        }
    }

    netif_is_initialized=0;
}

int ixc_netif_create(const char *devname,char res_devname[],int if_idx)
{
    int fd,flags;
    struct ixc_netif *netif=NULL;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        STDERR("wrong if index value\r\n");
        return -1;
    }

    netif=&netif_objs[if_idx];

    if(!netif_is_initialized){
        STDERR("please initialize netif\r\n");
        return -1;
    }

    if(netif->is_used){
        STDERR("ERROR:tap device has been opened\r\n");
    }

    strcpy(res_devname,devname);
    fd=tapdev_create(res_devname);

    if(fd<0) return -1;

    tapdev_up(res_devname);
    flags=fcntl(fd,F_GETFL,0);
    fcntl(fd,F_SETFL,flags | O_NONBLOCK);

    strcpy(netif->devname,res_devname);

    netif->is_used=1;
    netif->fd=fd;
    netif->type=if_idx;

    ixc_netif_refresh_hwaddr(if_idx);

    return fd;
}

void ixc_netif_delete(int if_idx)
{
    struct ixc_netif *netif;
    struct ixc_mbuf *m,*t;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        STDERR("wrong if index value\r\n");
        return;
    }

    if(!netif_is_initialized){
        STDERR("please initialize netif\r\n");
        return;
    }

    netif=&netif_objs[if_idx];

    if(!netif->is_used) return;

    tapdev_close(netif->fd,netif->devname);

    // 此处回收mbuf
    m=netif->sent_first;
    while(NULL!=m){
        t=m->next;
        ixc_mbuf_put(m);
        m=t;
    }
    netif->is_used=0;
}

int ixc_netif_set_ip(int if_idx,unsigned char *ipaddr,unsigned char prefix,int is_ipv6)
{
    unsigned char mask[16];
    struct ixc_netif *netif;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        STDERR("wrong if index value\r\n");
        return -1;
    }

    netif=&netif_objs[if_idx];

    if(!netif->is_used){
        STDERR("cannot set ip,it is not opened\r\n");
        return -1;
    }

    msk_calc(prefix,is_ipv6,mask);

    if(is_ipv6){
        memcpy(netif->ip6addr,ipaddr,16);
        memcpy(netif->mask_v6,mask,16);
    }else{
        memcpy(netif->ipaddr,ipaddr,4);
        memcpy(netif->mask_v4,mask,4);
    }

    return 0;
}

int ixc_netif_refresh_hwaddr(int if_idx)
{
    struct ixc_netif *netif;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        STDERR("wrong if index value\r\n");
        return -1;
    }

    netif=&netif_objs[if_idx];

    if(!netif->is_used){
        STDERR("cannot set ip,it is not opened\r\n");
        return -1;
    }
    
    return hwinfo_get(netif->devname,netif->hwaddr);
}

int ixc_netif_send(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=m->netif;

    if(!netif_is_initialized){
        STDERR("please initialize netif\r\n");
        return -1;
    }

    m->next=NULL;

    if(NULL==netif->sent_first){
        netif->sent_first=m;
    }else{
        netif->sent_last->next=m;
    }

    netif->sent_last=m;

    // 没有告知写入事件的告知需要加入写入事件
    if(!netif->write_flags){
        ixc_router_write_ev_tell(netif->fd,1);
        netif->write_flags=1;
    }

    return 0;
}

int ixc_netif_tx_data(struct ixc_netif *netif)
{
    struct ixc_mbuf *m;
    ssize_t wsize;
    int rs=0;

    if(!netif_is_initialized){
        STDERR("please initialize netif\r\n");
        return -1;
    }

    while(1){
        m=netif->sent_first;
        if(NULL==m) break;
        wsize=write(netif->fd,m->data+m->begin,m->end-m->begin);

        if(wsize<0){
            if(EAGAIN==errno){
                rs=0;
                break;
            }else{
                rs=-1;
                break;
            }
        }

        netif->sent_first=m->next;
        if(NULL==netif->sent_first) netif->sent_last=NULL;
        ixc_mbuf_put(m);
    }

    if(rs>=0 && NULL==netif->sent_first) {
        netif->write_flags=0;
        // 告知取消写入事件
        ixc_router_write_ev_tell(netif->fd,0);
    }

    return rs;
}

int ixc_netif_rx_data(struct ixc_netif *netif)
{
    ssize_t rsize;
    struct ixc_mbuf *m;
    int rs=0;
    
    if(!netif_is_initialized){
        STDERR("please initialize netif\r\n");
        return -1;
    }

    for(int n=0;n<IXC_NETIF_READ_NUM;n++){
        m=ixc_mbuf_get();
        if(NULL==m){
            rs=-1;
            STDERR("ERROR:cannot get mbuf\r\n");
            break;
        }

        m->netif=netif;
        m->next=NULL;

        rsize=read(netif->fd,m->data+IXC_MBUF_BEGIN,IXC_MBUF_END-IXC_MBUF_BEGIN);
        if(rsize<0){
            if(EAGAIN==errno){
                ixc_mbuf_put(m);
                rs=0;
                break;
            }else{
                ixc_mbuf_put(m);
                STDERR("ERROR:netif read error\r\n");
                rs=-1;
                break;
            }
        }

        m->begin=IXC_MBUF_BEGIN;
        m->offset=m->begin;
        m->tail=m->offset+rsize;
        m->end=m->tail;

        ixc_ether_handle(m);
    }

    return rs;
}

struct ixc_netif *ixc_netif_get(int if_idx)
{
    struct ixc_netif *netif;
    if(if_idx<0 || if_idx>IXC_NETIF_MAX) return NULL;

    netif=&netif_objs[if_idx];

    if(!netif->is_used) return NULL;

    return netif;
}

int ixc_netif_no_used_get(void)
{
    struct ixc_netif *netif;
    int rs=-1;

    for(int n=1;n<IXC_NETIF_MAX;n++){
        netif=&netif_objs[n];
        if(netif->is_used) continue;
        rs=n;
        break;
    }

    return rs;
}

int ixc_netif_is_used(int if_idx)
{
    struct ixc_netif *netif;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX) return 0;
    netif=&netif_objs[if_idx];

    return netif->is_used;
}