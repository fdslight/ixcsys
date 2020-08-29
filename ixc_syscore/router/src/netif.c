#include<stdio.h>
#include<stdlib.h>
#include<errno.h>

#include "netif.h"

#include "../../pywind/clib/debug.h"

int ixc_netif_create(const char *devname,char *res_devname[],int flags)
{
    return 0;
}

void ixc_netif_delete(const char *devname,int flags)
{

}

int ixc_netif_send(struct ixc_mbuf *m)
{
    return 0;
}

int ixc_netif_tx_data(struct ixc_netif *netif)
{
    struct ixc_mbuf *m=netif->sent_first,*t;
    ssize_t wsize;
    int rs=0;

    while(1){
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

        t=m->next;
        netif->sent_first=t;
        if(NULL==t) netif->sent_last=NULL;
        ixc_mbuf_put(m);
    }

    return rs;
}

int ixc_netif_rx_data(struct ixc_netif *netif)
{
    ssize_t rsize;
    for(int n=0;n<IXC_NETIF_READ_NUM;n++){

    }

    return 0;
}