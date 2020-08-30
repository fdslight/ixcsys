#include<stdlib.h>

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

        return m;
    }

    m=malloc(sizeof(struct ixc_mbuf));
    if(NULL==m){
        STDERR("no memory for struct ixc_mbuf\r\n");
        return NULL;
    }

    STDERR("get mbuf from malloc\r\n");

    m->next=NULL;
    m->netif=NULL;

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

        return;
    }

    m->next=ixc_mbuf_empty_head;
    ixc_mbuf_empty_head=m;
}