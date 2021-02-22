#include<string.h>
#include<stdlib.h>

#include "ip6unfrag.h"
#include "mbuf.h"

#include "../../../pywind/clib/timer.h"
#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"
#include "../../../pywind/clib/debug.h"

static struct ip6unfrag ip6unfrag;
static int ip6unfrag_is_initialized=0;
static struct time_wheel ip6unfrag_time_wheel;
static struct sysloop *ip6unfrag_sysloop;

static void ip6unfrag_map_del_cb(void *data)
{
    struct mbuf *m=data;
    struct time_data *tdata=m->priv_data;
    
    tdata->is_deleted=1;
    free(m);
}

static void ipunfrag_timeout_cb(void *data)
{
    char key[IP6UNFRAG_KEYSIZE];
    struct mbuf *m=data;
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);

    memcpy(&key[0],header->src_addr,4);
    memcpy(&key[4],header->dst_addr,4);
    memcpy(&key[8],(char *)(&(header->id)),2);

    map_del(ip6unfrag.m,key,ip6unfrag_map_del_cb);
}

static void ip6unfrag_sysloop_cb(struct sysloop *loop)
{
    time_wheel_handle(&ip6unfrag_time_wheel);
}

int ip6unfrag_init(void)
{
    struct map *m;
    int rs=map_new(&m,IP6UNFRAG_KEYSIZE);

    if(0!=rs){
        STDERR("cannot create map for ipunfrag\r\n");
        return -1;
    }

    // 这里的时间需要大于10s,因为系统IO阻塞时间为10s
    rs=time_wheel_new(&ip6unfrag_time_wheel,60,1,ipunfrag_timeout_cb,4096);
    if(0!=rs){
        map_release(m,NULL);
        STDERR("cannot create timer\r\n");
        return -1;
    }

    ip6unfrag_sysloop=sysloop_add(ip6unfrag_sysloop_cb,NULL);
    if(NULL==ip6unfrag_sysloop){
        time_wheel_release(&ip6unfrag_time_wheel);
        map_release(m,NULL);
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }

    bzero(&ip6unfrag,sizeof(struct ip6unfrag));

    ip6unfrag.m=m;
    ip6unfrag_is_initialized=1;

    return 0;
}

void ip6unfrag_uninit(void)
{
    map_release(ip6unfrag.m,ip6unfrag_map_del_cb);
    time_wheel_release(&ip6unfrag_time_wheel);

    ip6unfrag_is_initialized=0;
}

struct mbuf *ip6unfrag_add(struct mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);

    // 下一个可选头部必须为分帧头
    if(header->next_header!=44) return m;

    mbuf_put(m);

    return NULL;
}