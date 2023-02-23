#include<stdio.h>
#include<stdlib.h>
#include<errno.h>
#include<string.h>
#include<fcntl.h>
#include<unistd.h>
#include<sys/time.h>

#include "netif.h"
#include "router.h"
#include "ether.h"
#include "addr_map.h"
#include "route.h"
#include "debug.h"
#include "ip6.h"
#include "debug.h"
#include "npfwd.h"

#include "../../../pywind/clib/ev/ev.h"
#include "../../../pywind/clib/netif/tuntap.h"
#include "../../../pywind/clib/netif/hwinfo.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_netif netif_objs[IXC_NETIF_MAX];
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

static int ixc_netif_del_fn(struct ev *ev)
{
    struct ixc_netif *netif=ev->data;
    ixc_netif_delete(netif->type);

    return 0;
}

static void ixc_netif_calc_speed(struct ixc_netif *netif)
{
    unsigned long long old_sec;
    unsigned long long n_sec;
    unsigned long long v,speed;

    // 获取现在的时间
    n_sec=time(NULL);

    old_sec=netif->sec_time;

    v= n_sec-old_sec;

    // 小于5s不采集
    if(v < 5) return;

    speed= (netif->rx_traffic-netif->rx_traffic_old)/v;
    netif->rx_speed=speed;

    speed=(netif->tx_traffic-netif->tx_traffic_old)/v;
    netif->tx_speed=speed;

    netif->rx_traffic_old=netif->rx_traffic;
    netif->tx_traffic_old=netif->tx_traffic;

    netif->sec_time=n_sec;

}

int ixc_netif_init(struct ev_set *ev_set)
{
    netif_ev_set=ev_set;
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
    struct ixc_netif *netif=NULL;
    struct ev *ev;
    int fd=-1,rs;

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
        return -1;
    }

    bzero(netif,sizeof(struct ixc_netif));

    strcpy(res_devname,devname);
    fd=tapdev_create(res_devname);

    if(fd<0){
        STDERR("ERROR:cannot create tap device %s\r\n",res_devname);
        ixc_router_exit();
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

    EV_INIT_SET(ev,ixc_netif_readable_fn,ixc_netif_writable_fn,ixc_netif_timeout_fn,ixc_netif_del_fn,netif);
	rs=ev_modify(netif_ev_set,ev,EV_READABLE,EV_CTL_ADD);

	if(rs<0){
		ev_delete(netif_ev_set,ev);
		STDERR("cannot add to readablefor fd %d\r\n",fd);
		return -1;
	}

    netif->is_used=1;
    netif->fd=fd;
    netif->type=if_idx;
    netif->mtu_v4=1500;
    netif->mtu_v6=1280;
    netif->rx_traffic=0;
    netif->tx_traffic=0;

    bzero(netif->ipaddr,4);
    bzero(netif->ip6addr,16);

    netif->sec_time=time(NULL);

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
    unsigned char subnet[16];
    int rs=0;
    
    if(if_idx<0 || if_idx>=IXC_NETIF_MAX){
        STDERR("wrong if index value\r\n");
        return -1;
    }
    
    netif=&netif_objs[if_idx];

    if(!netif->is_used){
        STDERR("cannot set ip,it is not opened\r\n");
        return -1;
    }

    subnet_calc_with_prefix(ipaddr,prefix,is_ipv6,subnet);
    msk_calc(prefix,is_ipv6,mask);
    
    if(!is_ipv6){
        // 首先对原来的路由进行删除
        ixc_route_del(subnet,prefix,is_ipv6);
        rs=ixc_route_add(subnet,prefix,ipaddr,is_ipv6);

        if(rs<0){
            STDERR("cannot add route to system\r\n");
            return -1;
        }
    }

    if(is_ipv6){
        memcpy(netif->ip6addr,ipaddr,16);
        memcpy(netif->ip6_mask,mask,16);
        subnet_calc_with_prefix(ipaddr,prefix,1,netif->ip6_subnet);
        netif->isset_ip6=1;
        netif->ip6_prefix=prefix;
    }else{
        memcpy(netif->ipaddr,ipaddr,4);
        memcpy(netif->ip_mask,mask,4);
        subnet_calc_with_prefix(ipaddr,prefix,0,netif->ip_subnet);
        netif->isset_ip=1;
        netif->ip_prefix=prefix;
    }

    return 0;
}

int ixc_netif_set_hwaddr(int if_idx,unsigned char *hwaddr)
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

    //DBG_FLAGS;
    memcpy(netif->hwaddr,hwaddr,6);

    // 此处生成IPv6 local link相关信息
    ixc_ip6_local_link_get(hwaddr,netif->ip6_local_link_addr);
    bzero(netif->ip6_local_link_subnet,16);
    memcpy(netif->ip6_local_link_subnet,netif->ip6_local_link_addr,8);
    msk_calc(64,1,netif->ip6_local_link_mask);

    return 0;
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

        netif->tx_traffic+=wsize;

        netif->sent_first=m->next;
        if(NULL==netif->sent_first) netif->sent_last=NULL;
        ixc_mbuf_put(m);
    }

    // 加入到写入事件
    if(rs>=0 && NULL!=netif->sent_first) ev_modify(netif_ev_set,ev,EV_WRITABLE,EV_CTL_ADD);
    // 如果没有数据可写那么删除写事件
    if(NULL==netif->sent_first) ev_modify(netif_ev_set,ev,EV_WRITABLE,EV_CTL_DEL);

    ixc_netif_calc_speed(netif);

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

        netif->rx_traffic+=rsize;

        m->begin=IXC_MBUF_BEGIN;
        m->offset=m->begin;
        m->tail=m->offset+rsize;
        m->end=m->tail;

        if(IXC_NETIF_LAN==netif->type){
            m->from=IXC_MBUF_FROM_LAN;
        }
        else{
            m->from=IXC_MBUF_FROM_WAN;
        }
        ixc_ether_handle(m);
    }

    ixc_netif_calc_speed(netif);
    
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

int ixc_netif_is_subnet(struct ixc_netif *netif,unsigned char *ip,int is_ipv6,int is_ip6_local_link)
{
    unsigned char result[16];

    if(!is_ipv6){
        subnet_calc_with_msk(ip,netif->ip_mask,0,result);
        if(!memcmp(result,netif->ip_subnet,4)) return 1;
        return 0;
    }

    if(is_ip6_local_link){
        subnet_calc_with_msk(ip,netif->ip6_local_link_mask,1,result);
        if(!memcmp(result,netif->ip6_local_link_subnet,16)) return 1;
        return 0;
    }

    subnet_calc_with_msk(ip,netif->ip6_mask,1,result);
    if(!memcmp(result,netif->ip6_subnet,16)) return 1;

    return 0;
}

struct ixc_netif *ixc_netif_get_with_subnet_ip(unsigned char *ip,int is_ipv6)
{
    struct ixc_netif *rs=NULL,*netif=NULL;

    if(NULL==ip) return rs;

    for(int n=0;n<IXC_NETIF_MAX;n++){
        netif=&netif_objs[n];
        if(!netif->is_used) continue;
        if(!ixc_netif_is_subnet(netif,ip,is_ipv6,0)) continue;
        rs=netif;
        break;
    }

    return rs;
}

int ixc_netif_unset_ip(int if_idx,int is_ipv6)
{
    struct ixc_netif *netif=ixc_netif_get(if_idx);

    if(NULL==netif){
        STDERR("not found netif index %d\r\n",if_idx);
        return -1;
    }

    if(is_ipv6) netif->isset_ip6=0;
    else netif->isset_ip=0;

    return 0;
}

inline
int ixc_netif_wan_sendable(void)
{
    struct ixc_netif *netif=&netif_objs[IXC_NETIF_WAN];

    // 首先尝试清空数据
    ixc_netif_tx_data(netif);

    if(NULL==netif->sent_first) return 1;

    return 0;
}

int ixc_netif_mtu_set(int if_type,unsigned short v,int is_ipv6)
{
    struct ixc_netif *netif=ixc_netif_get(if_type);
    if(NULL==netif) return -1;

    if(v>1500) return -1;
    if(is_ipv6 && v<1280) return -1;
    
    if(is_ipv6) netif->mtu_v6=v;
    else netif->mtu_v4=v;

    return 0;
}

int ixc_netif_traffic_get(int if_type,unsigned long long *rx_traffic,unsigned long long *tx_traffic)
{
    struct ixc_netif *netif=ixc_netif_get(if_type);
    if(NULL==netif) return -1;

    *rx_traffic=netif->rx_traffic;
    *tx_traffic=netif->tx_traffic;

    return 0;
}

int ixc_netif_traffic_speed_get(int if_type,unsigned long long *rx_speed,unsigned long long *tx_speed)
{
    struct ixc_netif *netif=ixc_netif_get(if_type);
    if(NULL==netif) return -1;

    *rx_speed=netif->rx_speed;
    *tx_speed=netif->tx_speed;

    return 0;
}