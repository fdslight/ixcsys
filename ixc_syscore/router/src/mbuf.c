#include<stdlib.h>
#include<signal.h>
#include<unistd.h>
#include<string.h>

#include "mbuf.h"
#include "../../../pywind/clib/debug.h"

/// 空的mbuf
static struct ixc_mbuf *ixc_mbuf_empty_head=NULL;
/// 已经分配的mbuf数目
static size_t ixc_mbuf_used_num=0;
/// 预先分配的mbuf数目
static size_t ixc_mbuf_pre_alloc_num=0;
/// 是否初始化
static int ixc_mbuf_is_initialized=0;

int ixc_mbuf_init(size_t pre_alloc_num)
{
    struct ixc_mbuf *m=NULL;
    ixc_mbuf_is_initialized=1;

    for(size_t n=0;n<pre_alloc_num;n++){
        m=malloc(sizeof(struct ixc_mbuf));
        if(NULL==m){
            STDERR("no memory for pre alloc struct ixc_mbuf\r\n");
            ixc_mbuf_uninit();
            return -1;
        }
 
        m->next=ixc_mbuf_empty_head;
        ixc_mbuf_empty_head=m;
    }

    ixc_mbuf_used_num=pre_alloc_num;
    ixc_mbuf_pre_alloc_num=pre_alloc_num;

    return 0;
}

void ixc_mbuf_uninit(void)
{
    struct ixc_mbuf *m=ixc_mbuf_empty_head,*t;

    if(!ixc_mbuf_is_initialized){
        STDERR("no initialized\r\n");
        return;
    }

    while(NULL!=m){
        t=m->next;
        free(m);
        m=t;
    }
}

struct ixc_mbuf *ixc_mbuf_get(void)
{
    struct ixc_mbuf *m;

    if(!ixc_mbuf_is_initialized){
        STDERR("no initialized\r\n");
        return NULL;
    }

    if(NULL!=ixc_mbuf_empty_head){
        m=ixc_mbuf_empty_head;
        ixc_mbuf_empty_head=m->next;

        m->next=NULL;
        m->netif=NULL;
        m->loop_trace=0;

        return m;
    }

    m=malloc(sizeof(struct ixc_mbuf));
    if(NULL==m){
        STDERR("no memory for struct ixc_mbuf\r\n");
        return NULL;
    }

    //STDERR("get mbuf from malloc\r\n");
    
    m->next=NULL;
    m->netif=NULL;
    m->priv_data=NULL;
    m->priv_flags=0;
    m->loop_trace=0;
    m->passthrough=0;

    ixc_mbuf_used_num+=1;

    return m;
}

void ixc_mbuf_put(struct ixc_mbuf *m)
{
    if(!ixc_mbuf_is_initialized){
        STDERR("no initialized\r\n");
        return;
    }

    if(NULL==m) return;

    if(ixc_mbuf_used_num > ixc_mbuf_pre_alloc_num){
        free(m);
        ixc_mbuf_used_num-=1;
        DBG("mbuf free\r\n");
        return;
    }
    m->next=NULL;
    m->next=ixc_mbuf_empty_head;
    ixc_mbuf_empty_head=m;
}

struct ixc_mbuf *ixc_mbuf_clone(struct ixc_mbuf *m)
{
    struct ixc_mbuf *new_mbuf;

    if(NULL==m) return NULL;
    new_mbuf=ixc_mbuf_get();
    if(NULL==new_mbuf){
        STDERR("cannot get mbuf for clone\r\n");
        return NULL;
    }

    new_mbuf->next=NULL;
    new_mbuf->netif=m->netif;
    new_mbuf->priv_data=m->priv_data;
    new_mbuf->priv_flags=m->priv_flags;
    new_mbuf->is_ipv6=m->is_ipv6;
    new_mbuf->from=m->from;
    new_mbuf->begin=m->begin;
    new_mbuf->offset=m->offset;
    new_mbuf->tail=m->tail;
    new_mbuf->end=m->tail;
    new_mbuf->passthrough=m->passthrough;
    new_mbuf->link_proto=m->link_proto;

    memcpy(new_mbuf->next_host,m->next_host,16);
    memcpy(new_mbuf->dst_hwaddr,m->dst_hwaddr,6);
    memcpy(new_mbuf->src_hwaddr,m->src_hwaddr,6);

    memcpy(new_mbuf->data+new_mbuf->begin,m->data+m->begin,m->end-m->begin);

    return new_mbuf;
}