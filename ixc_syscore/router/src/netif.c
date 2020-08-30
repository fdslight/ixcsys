#include<stdio.h>
#include<stdlib.h>
#include<errno.h>
#include<string.h>
#include<fcntl.h>
#include<unistd.h>

#include "netif.h"
#include "router.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netif/tuntap.h"

static struct ixc_netif netif_obj;
static int netif_is_initialized=0;

int ixc_netif_init(void)
{
    bzero(&netif_obj,sizeof(struct ixc_netif));

    netif_is_initialized=1;

    return 0;
}

void ixc_netif_uninit(void)
{

}

int ixc_netif_create(const char *devname,char res_devname[])
{
    int fd,t,flags;
    struct ixc_netif *netif=&netif_obj;

    if(!netif_is_initialized){
        STDERR("please initialize netif\r\n");
        return -1;
    }

    strcpy(res_devname,devname);
    fd=tapdev_create(res_devname);

    if(fd<0) return -1;

    t=tapdev_up(res_devname);
    flags=fcntl(fd,F_GETFL,0);
    fcntl(fd,F_SETFL,flags | O_NONBLOCK);

    if(netif->is_used){
            STDERR("ERROR:tap device has been opened\r\n");
        tapdev_close(fd,res_devname);
        fd=-1;
    }else{
        strcpy(netif->devname,res_devname);
    }

    return fd;
}

void ixc_netif_delete(void)
{
    struct ixc_netif *netif=&netif_obj;
    struct ixc_mbuf *m,*t;

    if(!netif_is_initialized){
        STDERR("please initialize netif\r\n");
        return;
    }

    if(!netif->is_used) return;

    tapdev_close(netif->fd,netif->devname);

    // 此处回收mbuf
    m=netif->sent_first;
    while(NULL!=m){
        t=m->next;
        ixc_mbuf_put(m);
        m=t;
    }
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
                rs=1;
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
    }

    return rs;
}