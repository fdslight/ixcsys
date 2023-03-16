#include<time.h>
#include<string.h>

#include "traffic_log.h"
#include "debug.h"
#include "router.h"
#include "npfwd.h"
#include "mbuf.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/timer.h"
#include "../../../pywind/clib/sysloop.h"
#include "../../../pywind/clib/netutils.h"

static int traffic_log_is_initialized=0;
static int traffic_log_enable=0;

struct map *traffic_log_map=NULL;

struct time_wheel traffic_log_time_wheel;
struct sysloop *traffic_log_sysloop=NULL;

static void __ixc_traffic_log_send(struct ixc_traffic_log *log);

static void __ixc_traffic_log_sysloop_cb(struct sysloop *lp)
{
    //DBG_FLAGS;
    // 执行时间函数,定期检查NAT会话是否过期
    time_wheel_handle(&traffic_log_time_wheel);
}

static void __ixc_traffic_log_timeout_cb(void *data)
{
    struct ixc_traffic_log *log=data;
    
    __ixc_traffic_log_send(log);
    map_del(traffic_log_map,(char *)(log->hwaddr),NULL);
    free(log);
}

static unsigned long long __ixc_traffic_log_htonull(unsigned long long v)
{
    unsigned long long r=0;
    unsigned int x=v >> 32;

    x=htonl(x);
    r=x;
    r=r<<32;
    x=v & 0xffffffff;
    x=htonl(x);
    r|=x;

    return r;
}

static void __ixc_traffic_log_send(struct ixc_traffic_log *log)
{
    struct ixc_mbuf *m=ixc_mbuf_get();
    unsigned long long rx_traffic,tx_traffic;

    rx_traffic=log->rx_traffic;
    tx_traffic=log->tx_traffic;

    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return;
    }

    m->begin=m->offset=IXC_MBUF_BEGIN;
    m->end=m->tail=m->begin+sizeof(struct ixc_traffic_log);
    memcpy(m->data+m->begin,log,sizeof(struct ixc_traffic_log));

    log->rx_traffic=__ixc_traffic_log_htonull(rx_traffic);
    log->tx_traffic=__ixc_traffic_log_htonull(tx_traffic);

    ixc_npfwd_send_raw(m,0,IXC_FLAG_TRAFFIC_LOG);

    // 发送一次需要清零一次
    log->rx_traffic=0;
    log->tx_traffic=0;
}

int ixc_traffic_log_init(void)
{
    int rs;

    traffic_log_sysloop=sysloop_add(__ixc_traffic_log_sysloop_cb,NULL);
    if(NULL==traffic_log_sysloop){
        STDERR("cannot create sysloop\r\n");
        return -1;
    }

    rs=time_wheel_new(&traffic_log_time_wheel,10,IXC_IO_WAIT_TIMEOUT,__ixc_traffic_log_timeout_cb,256);
    if(0!=rs){
        sysloop_del(traffic_log_sysloop);
        STDERR("cannot create time wheel\r\n");
        return -1;
    }

    rs=map_new(&traffic_log_map,6);
    if(rs){
        STDERR("cannot create map\r\n");
        return -1;
    }

    traffic_log_is_initialized=1;
    traffic_log_enable=0;

    return 0;
}

void ixc_traffic_log_uninit(void)
{
    traffic_log_is_initialized=0;
}

/// 处理TCPIP协议
static void __ixc_traffic_log_statistics_tcpip(struct ixc_ether_header *header,struct ixc_traffic_log *log,int dir)
{
    struct netutil_iphdr *ip4_header=NULL;
    struct netutil_ip6hdr *ip6_header=NULL;

    unsigned char *host_addr;
    int is_ipv6=0;

    if(0x86dd==ntohs(header->type)) is_ipv6=1;
    
    if(is_ipv6){
        ip6_header=(struct netutil_ip6hdr *)(((char *)header)+14);

        if(IXC_TRAFFIC_LOG_DIR_OUT==dir) host_addr=ip6_header->src_addr;
        else host_addr=ip6_header->dst_addr;
    }else{
        ip4_header=(struct netutil_iphdr *)((char *)header+14);

        if(IXC_TRAFFIC_LOG_DIR_OUT==dir) host_addr=ip4_header->src_addr;
        else host_addr=ip4_header->dst_addr;
    }

    // 如果IP版本改变那么发送日志
    if(log->is_ipv6){
        if(!is_ipv6){
            __ixc_traffic_log_send(log);
            memcpy(log->host_addr,host_addr,4);
        }        
    }else{
        if(is_ipv6){
            __ixc_traffic_log_send(log);
            memcpy(log->host_addr,host_addr,16);
        }
    }
    log->is_ipv6=is_ipv6;
}

void ixc_traffic_log_statistics(struct ixc_ether_header *header,unsigned int size,int traffic_dir)
{
    struct ixc_traffic_log *log;
    struct time_data *tdata;
    unsigned char *hwaddr;
    int is_tcpip=1,rs;
    
    char is_found;

    if(!traffic_log_is_initialized){
        STDERR("not initialized traffic_log\r\n");
        return;
    }
    // 未开启不记录日志
    if(!traffic_log_enable) return;

    if(IXC_TRAFFIC_LOG_DIR_OUT==traffic_dir) hwaddr=header->src_hwaddr;
    else hwaddr=header->dst_hwaddr;

    log=map_find(traffic_log_map,(char *)hwaddr,&is_found);

    if(NULL==log){
        log=malloc(sizeof(struct ixc_traffic_log));
        if(NULL==log){
            STDERR("cannot malloc struct ixc_traffic_log\r\n");
            return;
        }
        bzero(log,sizeof(struct ixc_traffic_log));
        log->up_time=__ixc_traffic_log_htonull(time(NULL));

        tdata=time_wheel_add(&traffic_log_time_wheel,log,IXC_IO_WAIT_TIMEOUT);
        if(NULL==tdata){
            free(log);
            STDERR("cannot add to time wheel\r\n");
            return;
        }
        
        memcpy(log->hwaddr,hwaddr,6);
        rs=map_add(traffic_log_map,(char *)hwaddr,log);
        if(rs){
            tdata->is_deleted=1;
            free(log);
            STDERR("cannot add to map\r\n");
            return;
        }
    }

    if(IXC_TRAFFIC_LOG_DIR_OUT==traffic_dir) log->tx_traffic+=size;
    else log->rx_traffic+=size;

    switch(ntohs(header->type)){
        case 0x86dd:
        case 0x0800:
            break;
        default:
            is_tcpip=0;
            break;
    }

    // 协议改变发送日志
    if(log->is_tcpip){
        if(!is_tcpip) __ixc_traffic_log_send(log);
    }else{
        if(is_tcpip) __ixc_traffic_log_send(log);
    }

    log->is_tcpip=is_tcpip;
    if(log->is_tcpip) __ixc_traffic_log_statistics_tcpip(header,log,traffic_dir);
}

int ixc_traffic_log_enable(int enable)
{
    if(!traffic_log_is_initialized) return -1;

    traffic_log_enable=enable;

    return 0;
}