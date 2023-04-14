#include<stdlib.h>
#include<signal.h>
#include<unistd.h>
#include<string.h>

#include "sktbuf.h"
#include "../../../pywind/clib/debug.h"

/// 空的sktbuf
static struct ixc_sktbuf *ixc_sktbuf_empty_head=NULL;
/// 已经分配的sktbuf数目
static size_t ixc_sktbuf_used_num=0;
/// 预先分配的sktbuf数目
static size_t ixc_sktbuf_pre_alloc_num=0;
/// 是否初始化
static int ixc_sktbuf_is_initialized=0;

int ixc_sktbuf_init(size_t pre_alloc_num)
{
    struct ixc_sktbuf *m=NULL;
    ixc_sktbuf_is_initialized=1;

    for(size_t n=0;n<pre_alloc_num;n++){
        m=malloc(sizeof(struct ixc_sktbuf));
        if(NULL==m){
            STDERR("no memory for pre alloc struct ixc_sktbuf\r\n");
            ixc_sktbuf_uninit();
            return -1;
        }
 
        m->next=ixc_sktbuf_empty_head;
        ixc_sktbuf_empty_head=m;
    }

    ixc_sktbuf_used_num=pre_alloc_num;
    ixc_sktbuf_pre_alloc_num=pre_alloc_num;

    return 0;
}

void ixc_sktbuf_uninit(void)
{
    struct ixc_sktbuf *m=ixc_sktbuf_empty_head,*t;

    if(!ixc_sktbuf_is_initialized){
        STDERR("no initialized\r\n");
        return;
    }

    while(NULL!=m){
        t=m->next;
        free(m);
        m=t;
    }
}

struct ixc_sktbuf *ixc_sktbuf_get(void)
{
    struct ixc_sktbuf *m;

    if(!ixc_sktbuf_is_initialized){
        STDERR("no initialized\r\n");
        return NULL;
    }

    if(NULL!=ixc_sktbuf_empty_head){
        m=ixc_sktbuf_empty_head;
        ixc_sktbuf_empty_head=m->next;

        m->next=NULL;

        return m;
    }

    // 限制最大分配个数,防止分配过多造成系统内存不够
    if(ixc_sktbuf_used_num>=IXC_SKTBUF_MAX) return NULL;

    m=malloc(sizeof(struct ixc_sktbuf));
    if(NULL==m){
        STDERR("no memory for struct ixc_sktbuf\r\n");
        return NULL;
    }

    DBG("get sktbuf from malloc\r\n");
    
    m->next=NULL;

    ixc_sktbuf_used_num+=1;

    return m;
}

void ixc_sktbuf_put(struct ixc_sktbuf *m)
{
    if(!ixc_sktbuf_is_initialized){
        STDERR("no initialized\r\n");
        return;
    }

    if(NULL==m) return;

    if(ixc_sktbuf_used_num > ixc_sktbuf_pre_alloc_num){
        free(m);
        ixc_sktbuf_used_num-=1;
        DBG("sktbuf free\r\n");
        return;
    }
    m->next=NULL;
    m->next=ixc_sktbuf_empty_head;
    ixc_sktbuf_empty_head=m;
}

struct ixc_sktbuf *ixc_sktbuf_clone(struct ixc_sktbuf *m)
{
    struct ixc_sktbuf *new_sktbuf;

    if(NULL==m) return NULL;
    new_sktbuf=ixc_sktbuf_get();
    if(NULL==new_sktbuf){
        STDERR("cannot get sktbuf for clone\r\n");
        return NULL;
    }

    new_sktbuf->next=NULL;
    new_sktbuf->begin=m->begin;
    new_sktbuf->offset=m->offset;
    new_sktbuf->tail=m->tail;
    new_sktbuf->end=m->tail;

    memcpy(new_sktbuf->data+new_sktbuf->begin,m->data+m->begin,m->end-m->begin);

    return new_sktbuf;
}