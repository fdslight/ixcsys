
#include<string.h>

#include "vswitch.h"
#include "debug.h"
#include "ether.h"
#include "router.h"
#include "ether.h"
#include "npfwd.h"

#include "../../../pywind/clib/timer.h"
#include "../../../pywind/clib/sysloop.h"

static struct ixc_vsw_table vsw_table;
static struct time_wheel vsw_time_wheel;
static struct sysloop *vsw_sysloop=NULL;

static int vsw_is_initialized=0;


static void ixc_vsw_sysloop_cb(struct sysloop *loop)
{
    time_wheel_handle(&vsw_time_wheel);
}

static void ixc_vsw_del_cb(void *data)
{
    struct ixc_vsw_record *r=data;
    if(NULL!=r->tdata) r->tdata->is_deleted=1;
    free(r);
}

static void ixc_vsw_timeout_cb(void *data)
{
    struct ixc_vsw_record *r=data;
    struct time_data *tdata;

    time_t now=time(NULL);

    if(now-r->up_time >= IXC_VSW_TABLE_TIMEOUT){
        map_del(vsw_table.m,(char *)(r->hwaddr),ixc_vsw_del_cb);
        return;
    }

    tdata=time_wheel_add(&vsw_time_wheel,r,10);
    if(NULL==tdata){
        STDERR("cannot add to time wheel\r\n");
        map_del(vsw_table.m,(char *)(r->hwaddr),ixc_vsw_del_cb);
        return;
    }
    r->tdata=tdata;
}

int ixc_vsw_init(void)
{
    int rs;
    struct map *m;

    bzero(&vsw_table,sizeof(struct ixc_vsw_table));

    rs=time_wheel_new(&vsw_time_wheel,IXC_VSW_TABLE_TIMEOUT * 2/10,10,ixc_vsw_timeout_cb,256);

    if(0!=rs){
        STDERR("cannot create time wheel for init vswitch\r\n");
        return -1;
    }

    vsw_sysloop=sysloop_add(ixc_vsw_sysloop_cb,NULL);
    if(NULL==vsw_sysloop){
        time_wheel_release(&vsw_time_wheel);
        STDERR("cannot create sysloop for init vswitch\r\n");
        return -1;
    }


    rs=map_new(&m,6);
    if(rs!=0){
        time_wheel_release(&vsw_time_wheel);
        sysloop_del(vsw_sysloop);
        STDERR("cannot create map for init vswitch\r\n");
        return -1;
    }

    vsw_table.m=m;
    vsw_is_initialized=1;
    return 0;
}

void ixc_vsw_uninit(void)
{
    map_release(vsw_table.m,ixc_vsw_del_cb);
    sysloop_del(vsw_sysloop);
    time_wheel_release(&vsw_time_wheel);
}

/// 开启或者关闭虚拟交换
int ixc_vsw_enable(int enable)
{
    vsw_table.enable=enable;

    return 0;
}

/// 检查虚拟交换是否启用
inline
int ixc_vsw_is_enabled(void)
{
    return vsw_table.enable;
}

/// 加入到虚拟交换表
static int ixc_vsw_table_add(unsigned char *hwaddr,int flags)
{
    struct map *m=vsw_table.m;
    struct time_data *tdata;
    struct ixc_vsw_record *r=malloc(sizeof(struct ixc_vsw_record));
    int rs;

    if(NULL==r){
        STDERR("cannot create struct ixc_vsw_record\r\n");
        return -1;
    }

    tdata=time_wheel_add(&vsw_time_wheel,r,10);
    if(NULL==tdata){
        free(r);
        STDERR("cannot add to time wheel\r\n");
        return -1;
    }

    rs=map_add(m,(char *)hwaddr,r);
    if(rs<0){
        tdata->is_deleted=1;
        free(r);
        STDERR("cannot add to map\r\n");
        return -1;
    }

    bzero(r,sizeof(struct ixc_vsw_record));

    r->tdata=tdata;
    r->flags=flags;
    r->up_time=time(NULL);
    memcpy(r->hwaddr,hwaddr,6);

    return 0;
}

/// 处理MAC映射表存在的情况
static struct ixc_mbuf *ixc_vsw_handle_exists(struct ixc_mbuf *m,struct ixc_ether_header *header,struct ixc_vsw_record *r)
{
    r->up_time=time(NULL);
    // 如果是本地数据包那么直接返回
    if(IXC_VSW_FLG_LOCAL==r->flags) return m;
    
    //ixc_router_send(m->netif->type,0,IXC_FLAG_VSWITCH,m->data+m->offset,m->tail-m->offset);
    //ixc_mbuf_put(m);
    ixc_npfwd_send_raw(m,0,IXC_FLAG_VSWITCH);

    return NULL;
}

/// 处理MAC映射表不存在的情况
static struct ixc_mbuf *ixc_vsw_handle_no_exists(struct ixc_mbuf *m,struct ixc_ether_header *header)
{
    // 首先转发一遍数据包到应用空间
    //ixc_router_send(m->netif->type,0,IXC_FLAG_VSWITCH,m->data+m->offset,m->tail-m->offset);
    ixc_npfwd_send_raw(m,0,IXC_FLAG_VSWITCH);
    
    return m;
}

void ixc_vsw_handle(struct ixc_mbuf *m)
{
    struct ixc_vsw_record *r;
    struct ixc_mbuf *result;
    struct ixc_ether_header *eth_header=(struct ixc_ether_header *)(m->data+m->offset);
    char is_found;
    int rs;
    unsigned char all_zero[]={0x00,0x00,0x00,0x00,0x00,0x00};

    if(!vsw_table.enable){
        //DBG_FLAGS;
        ixc_ether_handle(m);
        return;
    }

    if(m->end-m->offset<14){
        ixc_mbuf_put(m);
        return;
    }

    // 多播地址本地和远程都发送一遍
    if((eth_header->dst_hwaddr[0] & 0x01)==0x01 || !memcmp(all_zero,eth_header->dst_hwaddr,6)){
        result=ixc_mbuf_clone(m);
        if(NULL!=result) ixc_npfwd_send_raw(result,0,IXC_FLAG_VSWITCH);
        //ixc_router_send(m->netif->type,0,IXC_FLAG_VSWITCH,m->data+m->offset,m->tail-m->offset);
        ixc_ether_handle(m);
        return;
    }

    // 本机的处理方式
    if(!memcmp(m->netif->hwaddr,eth_header->dst_hwaddr,6)){
        ixc_ether_handle(m);
        return;
    }

    r=map_find(vsw_table.m,(char *)(eth_header->src_hwaddr),&is_found);
    
    // 源端MAC地址不存在那么添加记录
    if(NULL==r) {
        rs=ixc_vsw_table_add(eth_header->src_hwaddr,IXC_VSW_FLG_LOCAL);
        if(rs<0){
            STDERR("cannot add to vswitch table\r\n");
            ixc_mbuf_put(m);
            return;
        }
        //IXC_PRINT_HWADDR("BBB------------------ ",eth_header->src_hwaddr);
    }else{
        r->flags=IXC_VSW_FLG_LOCAL;
    }

    r=map_find(vsw_table.m,(char *)(eth_header->dst_hwaddr),&is_found);
    if(NULL==r) result=ixc_vsw_handle_no_exists(m,eth_header);
    else result=ixc_vsw_handle_exists(m,eth_header,r);
    
    if(NULL!=result) ixc_ether_handle(result);
}

int ixc_vsw_send(void *data,size_t size)
{
    struct ixc_ether_header *eth_header=(struct ixc_ether_header *)data;
    struct ixc_mbuf *m;
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);

    if(!vsw_table.enable){
        STDERR("no enable vswitch\r\n");
        return -1;
    }

    if(size<22) return -1;
    // 检查MAC地址是否合法,源地址和目标地址一致那么就丢弃数据包
    if(!memcmp(eth_header->src_hwaddr,eth_header->dst_hwaddr,6)) return -1;
    
    m=ixc_mbuf_get();
    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return -1;
    }

    m->next=NULL;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=IXC_MBUF_BEGIN;
    m->tail=IXC_MBUF_BEGIN+size;
    m->end=IXC_MBUF_BEGIN+size;
    m->netif=netif;
    m->from=IXC_MBUF_FROM_LAN;

    memcpy(m->data+m->offset,data,size);

    return ixc_vsw_send2(m);
}

int ixc_vsw_send2(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_LAN);
    struct ixc_ether_header *eth_header=(struct ixc_ether_header *)(m->data+m->offset);
    struct ixc_mbuf *m2;
    struct ixc_vsw_record *r;
    char is_found;
    unsigned char all_zero[]={0x00,0x00,0x00,0x00,0x00,0x00};
    int rs;

    // 如果没有开启那么就丢弃数据包
    if(!vsw_table.enable){
        ixc_mbuf_put(m);
        STDERR("no enable vswitch\r\n");
        return -1;
    }

    if(!memcmp(eth_header->dst_hwaddr,netif->hwaddr,6)){
        ixc_ether_handle(m);
        return 0;
    }

    // 检查是否是多播地址
    if((eth_header->dst_hwaddr[0] & 0x01)==0x01 || !memcmp(all_zero,eth_header->dst_hwaddr,6)){
        ixc_ether_send2(m);
        m2=ixc_mbuf_clone(m);
        if(NULL==m2){
            STDERR("cannot get mbuf for multi broadcast\r\n");
            return -1;
        }
        ixc_ether_handle(m2);
        return 0;
    }

    r=map_find(vsw_table.m,(char *)(eth_header->src_hwaddr),&is_found);

    // 记录存在那么直接发送
    if(NULL!=r){
        r->up_time=time(NULL);
        r->flags=IXC_VSW_FLG_FWD;
        ixc_ether_send2(m);
        return 0;
    }

    rs=ixc_vsw_table_add(eth_header->src_hwaddr,IXC_VSW_FLG_FWD);
    if(rs<0){
        STDERR("cannot add to vswitch table\r\n");
        ixc_mbuf_put(m);
        return -1;
    }
    ixc_ether_handle(m);

    return 0;
}