#include<stdio.h>
#include<stdlib.h>
#include<errno.h>
#include<string.h>
#include<fcntl.h>
#include<unistd.h>
#include<sys/time.h>

#include "netif.h"
#include "npfwd.h"

#include "../../pywind/clib/ev/ev.h"
#include "../../pywind/clib/netif/tuntap.h"

static struct ixc_netif my_netif;
static struct ev_set *netif_ev_set;
static int netif_is_initialized=0;


static int ixc_netif_readable_fn(struct ev *ev)
{
    struct ixc_netif *netif=ev->data;

    ixc_netif_rx_data(netif);

    return 0;
}

static int ixc_netif_writable_fn(struct ev *ev)
{
    struct ixc_netif *netif=ev->data;

    ixc_netif_tx_data(netif);

    return 0;
}

static int ixc_netif_timeout_fn(struct ev *ev)
{
    return 0;
}

int ixc_netif_init(struct ev_set *ev_set)
{
    netif_ev_set=ev_set;
    bzero(&my_netif,sizeof(struct ixc_netif));

    netif_is_initialized=1;

    return 0;
}

void ixc_netif_uninit(void)
{
    if(!netif_is_initialized) return;

    ixc_netif_delete();

    netif_is_initialized=0;
}

int ixc_netif_create(const char *devname)
{
    struct ixc_netif *netif=&my_netif;
    struct ev *ev;
    int fd=-1,rs;
    char res_devname[4096];

    if(!netif_is_initialized){
        STDERR("please initialize netif\r\n");
        return -1;
    }

    if(netif->is_used){
        STDERR("ERROR:tap device has been opened\r\n");
        return -1;
    }

    bzero(netif,sizeof(struct ixc_netif));

    strcpy(res_devname,devname);
    fd=tapdev_create(res_devname);

    if(fd<0){
        STDERR("ERROR:cannot create tap device %s\r\n",res_devname);
        return -1;
    }

    tapdev_up(res_devname);

    tapdev_set_nonblocking(fd);
    strcpy(netif->devname,res_devname);

    ev=ev_create(netif_ev_set,fd);
    if(NULL==ev){
        tapdev_close(fd,res_devname);
        STDERR("cannot ev for netif %s\r\n",res_devname);
        return -1;
    }

    EV_INIT_SET(ev,ixc_netif_readable_fn,ixc_netif_writable_fn,ixc_netif_timeout_fn,NULL,netif);
	rs=ev_modify(netif_ev_set,ev,EV_READABLE,EV_CTL_ADD);

	if(rs<0){
        ixc_netif_delete();
		STDERR("cannot add to readablefor fd %d\r\n",fd);
		return -1;
	}

    netif->is_used=1;
    netif->fd=fd;

    return fd;
}

void ixc_netif_delete()
{
    struct ixc_netif *netif=&my_netif;
    struct ixc_mbuf *m,*t;

    if(!netif->is_used) return;

    ev_delete(netif_ev_set,ev_get(netif_ev_set,netif->fd));

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

int ixc_netif_send(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=&my_netif;

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

    ixc_netif_tx_data(netif);

    return 0;
}

int ixc_netif_tx_data(struct ixc_netif *netif)
{
    struct ixc_mbuf *m;
    struct ev *ev=ev_get(netif_ev_set,netif->fd);
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
        
        //STDERR("%x:%x:%x:%x:%x:%x\r\n",m->src_hwaddr[0],m->src_hwaddr[1],m->src_hwaddr[2],m->src_hwaddr[3],m->src_hwaddr[4],m->src_hwaddr[5]);

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

    // 加入到写入事件
    if(rs>=0 && NULL!=netif->sent_first) ev_modify(netif_ev_set,ev,EV_WRITABLE,EV_CTL_ADD);
    // 如果没有数据可写那么删除写事件
    if(NULL==netif->sent_first) ev_modify(netif_ev_set,ev,EV_WRITABLE,EV_CTL_DEL);

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
            //STDERR("ERROR:cannot get mbuf\r\n");
            break;
        }

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

        ixc_npfwd_send(m);
    }
    
    return rs;
}

struct ixc_netif *ixc_netif_get(void)
{
    struct ixc_netif *netif=&my_netif;

    if(!netif->is_used) return NULL;

    return netif;
}


