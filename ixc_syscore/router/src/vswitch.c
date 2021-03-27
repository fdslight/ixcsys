
#include<string.h>

#include "vswitch.h"
#include "debug.h"
#include "ether.h"
#include "router.h"

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

static void ixc_vsw_timeout_cb(void *data)
{
    struct ixc_vsw_record *r=data;
}

static void ixc_vsw_del_cb(void *data)
{
    struct ixc_vsw_record *r=data;
}

/// 加入到虚拟交换表
static int ixc_vsw_add_to_vstable(unsigned char *hwaddr,int flags)
{
    struct ixc_vsw_record *r=malloc(sizeof(struct ixc_vsw_record));
    struct time_data *tdata;

    if(NULL==r){
        STDERR("cannot malloc for struct ixc_vsw_record\r\n");
        return -1;
    }

    tdata=time_wheel_add(&vsw_time_wheel,r,10);
    if(NULL==tdata){
        free(r);
        STDERR("cannot add to time wheel\r\n");
        return -1;
    }

    bzero(r,sizeof(struct ixc_vsw_record));

    r->up_time=time(NULL);
    r->tdata=tdata;
    r->flags=flags;

    memcpy(r->hwaddr,hwaddr,6);

    return 0;
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
    if(NULL!=vsw_sysloop){
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

/// 处理MAC映射表存在的情况
static struct ixc_mbuf *ixc_vsw_handle_exists(struct ixc_mbuf *m,struct ixc_ether_header *header,struct ixc_vsw_record *r)
{
    r->up_time=time(NULL);
    // 如果是本地数据包那么直接返回
    if(IXC_VSW_FLG_LOCAL==r->flags) return m;
    
    ixc_router_send(m->netif->type,0,IXC_FLAG_VSWITCH,m->data+m->offset,m->tail-m->offset);
    ixc_mbuf_put(m);

    return NULL;
}

/// 处理MAC映射表不存在的情况
static struct ixc_mbuf *ixc_vsw_handle_no_exists(struct ixc_mbuf *m,struct ixc_ether_header *header)
{
    // 首先转发一遍数据包到应用空间
    ixc_router_send(m->netif->type,0,IXC_FLAG_VSWITCH,m->data+m->offset,m->tail-m->offset);
    
    return m;
}

struct ixc_mbuf *ixc_vsw_handle(struct ixc_mbuf *m)
{
    struct ixc_vsw_record *r;
    struct ixc_mbuf *result;
    struct ixc_ether_header *eth_header=(struct ixc_ether_header *)(m->data+m->offset);
    char is_found;

    if(!vsw_table.enable) return m;

    r=map_find(vsw_table.m,(char *)(eth_header->dst_hwaddr),&is_found);
    
    if(NULL==r) result=ixc_vsw_handle_no_exists(m,eth_header);
    else result=ixc_vsw_handle_exists(m,eth_header,r);

    return result;
}

int ixc_vsw_send(void *data,size_t size)
{
    if(size<14) return -1;

    return 0;
}