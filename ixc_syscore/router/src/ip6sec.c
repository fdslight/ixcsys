#include<stdlib.h>
#include<string.h>

#include<time.h>

#include "ip6sec.h"
#include "debug.h"
#include "router.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/timer.h"
#include "../../../pywind/clib/sysloop.h"

static struct ixc_ip6sec ip6sec;

static struct time_wheel ip6sec_time_wheel;

static struct sysloop *ip6sec_sysloop=NULL;

static int ip6sec_is_initialized=0;

static void ixc_ip6sec_del_cb(void *data)
{
    struct ixc_ip6sec_info *info=data;
    struct time_data *tdata=info->tdata;

    if(NULL!=tdata) tdata->is_deleted=1;

    free(info);
}


static void ixc_ip6sec_timeout_cb(void *data)
{
    struct ixc_ip6sec_info *sec_info=data;
    struct time_data *tdata;
    time_t now=time(NULL);
    time_t x=now-sec_info->up_time;

    if(x>IXC_IP6SEC_TIMEOUT){
        DBG("IPv6 security map timeout\r\n");
        map_del(ip6sec.m,sec_info->key,ixc_ip6sec_del_cb);
        return;
    }

    tdata=time_wheel_add(&ip6sec_time_wheel,sec_info,IXC_IO_WAIT_TIMEOUT);
    if(NULL==tdata){
        STDERR("cannot add to time wheel for IPv6 security\r\n");
        map_del(ip6sec.m,sec_info->key,ixc_ip6sec_del_cb);
        return;
    }

    sec_info->tdata=tdata;
}

static void ixc_ip6sec_sysloop_cb(struct sysloop *loop)
{
    time_wheel_handle(&ip6sec_time_wheel);
}

static int ixc_ip6sec_add(const char key[],int is_tmp)
{
    struct ixc_ip6sec_info *sec_info;
    struct time_data *tdata;
    int rs;

    sec_info=malloc(sizeof(struct ixc_ip6sec_info));
    if(NULL==sec_info){
        STDERR("cannot malloc struct ixc_ip6sec_info\r\n");
        return -1;
    }
    bzero(sec_info,sizeof(struct ixc_ip6sec_info));

    rs=map_add(ip6sec.m,key,sec_info);
    if(rs!=0){
        free(sec_info);

        STDERR("cannot add to map\r\n");
        return -1;
    }

    if(is_tmp){
        tdata=time_wheel_add(&ip6sec_time_wheel,sec_info,IXC_IO_WAIT_TIMEOUT);
        if(NULL==tdata){
            free(sec_info);
            map_del(ip6sec.m,key,NULL);

            STDERR("cannot add to time wheel\r\n");
            return -1;
        }
        sec_info->tdata=tdata;
    }

    memcpy(sec_info->key,key,IXC_IP6SEC_KEYSIZE);
    sec_info->up_time=time(NULL);

    return 0;
}

int ixc_ip6sec_init(void)
{
    int rs;
    bzero(&ip6sec,sizeof(struct ixc_ip6sec));

    rs=map_new(&(ip6sec.m),IXC_IP6SEC_KEYSIZE);

    if(rs!=0){
        STDERR("cannot add to map for IPv6 security\r\n");
        return -1;
    }

    ip6sec_sysloop=sysloop_add(ixc_ip6sec_sysloop_cb,NULL);

    if(NULL==ip6sec_sysloop){
        map_release(ip6sec.m,NULL);
        STDERR("cannot add to sysloop for IPv6 security\r\n");
        return -1;
    }

    rs=time_wheel_new(&ip6sec_time_wheel,IXC_IP6SEC_TIMEOUT*2/IXC_IO_WAIT_TIMEOUT,IXC_IO_WAIT_TIMEOUT,ixc_ip6sec_timeout_cb,512);

    if(rs!=0){
        map_release(ip6sec.m,NULL);
        sysloop_del(ip6sec_sysloop);
        STDERR("cannot init time wheel for ipv6 security\r\n");
        return -1;
    }

    ip6sec_is_initialized=1;

    return 0;
}

void ixc_ip6sec_uninit(void)
{
    map_release(ip6sec.m,ixc_ip6sec_del_cb);
    sysloop_del(ip6sec_sysloop);
    time_wheel_release(&ip6sec_time_wheel);

    ip6sec_is_initialized=0;
}

int ixc_ip6sec_check_ok(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);
    char key[IXC_IP6SEC_KEYSIZE];
    struct ixc_ip6sec_info *sec_info;
    char is_found;
    int rs;

    // 如果未启用IPv6安全,那么始终认为安全通过
    if(!ip6sec.enable) return 1;
    if(header->next_header==58) return 1;

    if(m->from==IXC_MBUF_FROM_LAN){
        memcpy(&key[0],header->src_addr,16);
        memcpy(&key[16],header->dst_addr,16);
    }else{
        memcpy(&key[0],header->dst_addr,16);
        memcpy(&key[16],header->src_addr,16);
    }
   
    //DBG_FLAGS;
    sec_info=map_find(ip6sec.m,key,&is_found);
    // 检查WAN网口流进来的流量
    if(m->from==IXC_MBUF_FROM_WAN){
        // 找不到访问记录那么就删除
        if(NULL==sec_info){
            IXC_PRINT_IP6("src address ",header->src_addr);
            IXC_PRINT_IP6("dst address ",header->dst_addr);
            DBG("next header %d\r\n",header->next_header);
            return 0;
        }
        return 1;
    }

    if(NULL==sec_info){
        rs=ixc_ip6sec_add(key,1);
        if(0!=rs){
            STDERR("cannot add to ipv6 security record\r\n");
            return 0;
        }
        sec_info=map_find(ip6sec.m,key,&is_found);
    }

    sec_info->up_time=time(NULL);
    //DBG_FLAGS;
    return 1;
}

int ixc_ip6sec_enable(int enable)
{
    ip6sec.enable=enable;
    return 0;
}