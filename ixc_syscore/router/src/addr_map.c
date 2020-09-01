
#include<string.h>
#include<time.h>

#include "addr_map.h"
#include "arp.h"

#include "../../../pywind/clib/debug.h"

static struct ixc_addr_map addr_map;
static int addr_map_is_initialized=0;

static void ixc_addr_map_timeout_cb(void *data)
{
    struct ixc_addr_map_record *r=data;
    struct time_data *tdata=r->tdata;

    time_t now_time=time(NULL);

    // 超时释放内存
    if(now_time - r->up_time >= IXC_ADDR_MAP_TIMEOUT){
        tdata->is_deleted=1;
        free(r);
        return;
    }

    tdata->is_deleted=1;
    tdata=time_wheel_add(&(addr_map.time_wheel),r,now_time-r->up_time);
    
    r->tdata=tdata;

    // 对IPv6的处理方式
    if(r->is_ipv6){
        return;
    }

    // 发送ARP请求,检查ARP记录
    ixc_arp_send(r->netif,r->hwaddr,r->address,IXC_ARP_OP_REQ);
}

static void ixc_addr_map_del_cb(void *data)
{
    struct ixc_addr_map_record *r=data;
    struct time_data *tdata=r->tdata;

    tdata->is_deleted=1;
    free(r);
}

int ixc_addr_map_init(void)
{
    int rs;
    struct map *m;
    bzero(&addr_map,sizeof(struct ixc_addr_map));

    rs=time_wheel_new(&(addr_map.time_wheel),IXC_ADDR_MAP_TIMEOUT*2/10,10,ixc_addr_map_timeout_cb,256);
    if(rs){
        STDERR("cannot create time wheel for address map\r\n");
        return -1;
    }

    rs=map_new(&m,4);
    if(rs){
        time_wheel_release(&(addr_map.time_wheel));
        STDERR("cannot create map for ipv4 address map\r\n");
        return -1;
    }

    addr_map.ip_record=m;
    rs=map_new(&m,16);
    if(rs){
        map_release(addr_map.ip_record,NULL);
        time_wheel_release(&(addr_map.time_wheel));
        STDERR("cannot create map for ipv6 address map\r\n");
        return -1;
    }

    addr_map.ip6_record=m;
    addr_map_is_initialized=1;

    return 0;
}

void ixc_addr_map_uninit(void)
{
    if(!addr_map_is_initialized) return;

    map_release(addr_map.ip_record,ixc_addr_map_del_cb);
    map_release(addr_map.ip6_record,ixc_addr_map_del_cb);

    time_wheel_release(&(addr_map.time_wheel));

    addr_map_is_initialized=0;
}

int ixc_addr_map_add(struct ixc_netif *netif,unsigned char *ip,unsigned char *hwaddr,int is_ipv6)
{
    struct time_data *tdata;
    struct ixc_addr_map_record *r;
    struct map *map;
    char is_found;
    int rs;

    if(!addr_map_is_initialized){
        STDERR("addr map not initialized\r\n");
        return -1;
    }

    map=is_ipv6?addr_map.ip6_record:addr_map.ip_record;
    r=map_find(map,(char *)ip,&is_found);
    // 如果找的到记录那么直接返回
    if(NULL!=r) return 0;
    
    r=malloc(sizeof(struct ixc_addr_map_record));
    if(NULL==r){
        STDERR("cannot malloc for struct ixc_addr_map_record\r\n");
        return -1;
    }

    rs=map_add(map,(char *)ip,r);
    if(rs){
        STDERR("map add fail\r\n");
        free(r);
        return -1;
    }

    tdata=time_wheel_add(&(addr_map.time_wheel),r,IXC_ADDR_MAP_TIMEOUT*0.8);
    if(NULL==tdata){
        STDERR("cannot add to timer\r\n");
        map_del(map,(char *)ip,NULL);
        free(r);
        return -1;
    }

    r->netif=netif;
    r->tdata=tdata;

    if(is_ipv6) memcpy(r->address,ip,16);
    else memcpy(r->address,ip,4);

    r->is_ipv6=is_ipv6;

    memcpy(r->hwaddr,hwaddr,6);
    r->up_time=time(NULL);

    return 0;
}

struct ixc_addr_map_record *ixc_addr_map_get(unsigned char *ip,int is_ipv6)
{
    struct ixc_addr_map_record *r=NULL;
    struct map *map;
    char is_found;

    map=is_ipv6?addr_map.ip6_record:addr_map.ip_record;
    r=map_find(map,(char *)ip,&is_found);

    return r;
}

void ixc_addr_map_do(void)
{
    if(!addr_map_is_initialized){
        STDERR("addr map not initialized\r\n");
        return;
    }
    time_wheel_handle(&(addr_map.time_wheel));
}

