#include<string.h>
#include<errno.h>
#include<unistd.h>

#include "local.h"
#include "ip.h"
#include "router.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netif/tuntap.h"

static int tundev_fd=-1;
static char tundev_name[4096];
static int tundev_is_initialized=0;

static unsigned char local_ipaddr[4];

/// 全局单一IPv6地址
static unsigned char local_uniq_ip6addr[16];
/// 全局链路地址
static unsigned char local_linked_ip6addr[16];

struct ixc_mbuf *local_mbuf_sent_first=NULL;
struct ixc_mbuf *local_mbuf_sent_last=NULL;

/// 写入标志
static int tundev_wflags=0;

int ixc_local_init(void)
{
    bzero(local_ipaddr,4);
    bzero(local_uniq_ip6addr,16);
    bzero(local_linked_ip6addr,16);

    return 0;
}

void ixc_local_uninit(void)
{
    if(!tundev_is_initialized) return;
    if(tundev_fd>0) ixc_local_dev_delete();

    tundev_is_initialized=0;
}

int ixc_local_dev_create(char *name)
{
    int fd;

    if(tundev_fd>0){
        STDERR("the tun device has been created\r\n");
        return -1;
    }

    fd=tundev_create(name);
    if(fd<0) return fd;

    tundev_up(name);
    tundev_set_nonblocking(fd);
    tundev_fd=fd;

    strcpy(tundev_name,name);
    
    return fd;
}/// 删除tun设备

void ixc_local_dev_delete(void)
{
    struct ixc_mbuf *m,*t;

    if(!tundev_is_initialized) return;
    if(tundev_fd<0) return;

    tundev_close(tundev_fd,tundev_name);

    m=local_mbuf_sent_first;
    while(NULL!=m){
        t=m->next;
        ixc_mbuf_put(m);
        m=t;
    }
    tundev_fd=-1;
}

int ixc_local_rx_data(void)
{
    struct ixc_mbuf *m;
    ssize_t rsize;
    int rs=0;

    for(int n=0;n<IXC_LOCAL_READ_NUM;n++){
        m=ixc_mbuf_get();
        if(NULL==m){
            STDERR("cannot get mbuf\r\n");
            break;
        }

        m->netif=NULL;
        m->next=NULL;

        rsize=read(tundev_fd,m->data+IXC_MBUF_BEGIN,IXC_MBUF_END-IXC_MBUF_BEGIN);
        
        if(rsize<0){
            if(EAGAIN==errno){
                ixc_mbuf_put(m);
                rs=0;
                break;
            }else{
                ixc_mbuf_put(m);
                STDERR("ERROR:tundev read error\r\n");
                rs=-1;
                break;
            }
        }

        m->begin=IXC_MBUF_BEGIN;
        m->offset=m->begin;
        m->tail=m->offset+rsize;
        m->end=m->tail;

        ixc_ip_send(m);
    }

    return rs;
}

int ixc_local_tx_data(void)
{
    struct ixc_mbuf *m;
    ssize_t wsize;
    int rs=0;

    while(1){
        m=local_mbuf_sent_first;
        if(NULL==m) break;
        wsize=write(tundev_fd,m->data+m->begin,m->end-m->begin);

        if(wsize<0){
            if(EAGAIN==errno){
                rs=0;
                break;
            }else{
                rs=-1;
                break;
            }
        }

        if(NULL==local_mbuf_sent_first) local_mbuf_sent_last=NULL;
        ixc_mbuf_put(m);
    }

    if(rs>=0 && NULL==local_mbuf_sent_first) {
        tundev_wflags=0;
        // 告知取消写入事件
        ixc_router_write_ev_tell(tundev_fd,0);
    }

    return rs;
}

int ixc_local_set_ip(unsigned char *ipaddr,int is_ipv6,int is_ipv6_local_linked)
{
    if(!tundev_is_initialized){
        STDERR("please initialized local\r\n");
        return -1;
    }

    if(is_ipv6){
        if(is_ipv6_local_linked) memcpy(local_linked_ip6addr,ipaddr,16);
        else memcpy(local_uniq_ip6addr,ipaddr,16);
    }else{
        memcpy(local_ipaddr,ipaddr,4);
    }
    
    return 0;
}

void ixc_local_send(struct ixc_mbuf *m)
{
    if(NULL==m) return;

    if(tundev_fd<0){
        STDERR("then tun device not found\r\n");
        return;
    }
    m->next=NULL;

    if(NULL==local_mbuf_sent_first){
        local_mbuf_sent_first=m;
    }else{
        local_mbuf_sent_last->next=m;
    }

    local_mbuf_sent_last=m;

    if(!tundev_wflags){
        ixc_router_write_ev_tell(tundev_fd,1);
        tundev_wflags=1;
    }
}

inline
unsigned char *ixc_local_get(int is_ipv6,int is_ipv6_local_linked)
{
    if(!is_ipv6) return local_ipaddr;
    if(is_ipv6_local_linked) return local_linked_ip6addr;

    return local_uniq_ip6addr;
}