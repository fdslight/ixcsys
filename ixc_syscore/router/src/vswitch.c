
#include<string.h>

#include "vswitch.h"
#include "debug.h"
#include "ether.h"

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
    return NULL;
}

/// 处理MAC映射表不存在的情况
static struct ixc_mbuf *ixc_vsw_handle_no_exists(struct ixc_mbuf *m,struct ixc_ether_header *header)
{
    
    return NULL;
}

struct ixc_mbuf *ixc_vsw_handle(struct ixc_mbuf *m)
{
    struct ixc_vsw_record *r;
    struct ixc_mbuf *result;
    struct ixc_ether_header *eth_header=(struct ixc_ether_header *)(m->data+m->offset);
    char is_found;

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