#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <string.h>

#include "mbuf.h"
#include "../../../pywind/clib/debug.h"

/// 空的mbuf
static struct ixc_mbuf *ixc_mbuf_empty_head = NULL;
/// 已经分配的mbuf数目
static size_t ixc_mbuf_used_num = 0;
/// 预先分配的mbuf数目
static size_t ixc_mbuf_pre_alloc_num = 0;
/// 是否初始化
static int ixc_mbuf_is_initialized = 0;
/// 锁标志
static int ixc_mbuf_lock = 0;

int ixc_mbuf_init(size_t pre_alloc_num)
{
    struct ixc_mbuf *m = NULL;
    ixc_mbuf_is_initialized = 1;
    ixc_mbuf_lock = 0;

    for (size_t n = 0; n < pre_alloc_num; n++)
    {
        m = malloc(sizeof(struct ixc_mbuf));
        if (NULL == m)
        {
            STDERR("no memory for pre alloc struct ixc_mbuf\r\n");
            ixc_mbuf_uninit();
            return -1;
        }

        m->next = ixc_mbuf_empty_head;
        ixc_mbuf_empty_head = m;
    }

    ixc_mbuf_used_num = pre_alloc_num;
    ixc_mbuf_pre_alloc_num = pre_alloc_num;

    return 0;
}

void ixc_mbuf_uninit(void)
{
    struct ixc_mbuf *m = ixc_mbuf_empty_head, *t;

    if (!ixc_mbuf_is_initialized)
    {
        STDERR("no initialized\r\n");
        return;
    }

    while (NULL != m)
    {
        t = m->next;
        free(m);
        m = t;
    }
}

static void __ixc_mbuf_lock(void)
{
    while (1)
    {
        if (ixc_mbuf_lock)
            continue;
        ixc_mbuf_lock = 1;
        break;
    }
}

static void __ixc_mbuf_unlock(void)
{
    ixc_mbuf_lock = 0;
}

static struct ixc_mbuf *__ixc_mbuf_get(void)
{
    struct ixc_mbuf *m;

    if (!ixc_mbuf_is_initialized)
    {
        STDERR("no initialized\r\n");
        return NULL;
    }

    if (NULL != ixc_mbuf_empty_head)
    {
        m = ixc_mbuf_empty_head;
        ixc_mbuf_empty_head = m->next;

        m->next = NULL;
        m->loop_trace = 0;

        return m;
    }

    // 限制最大分配个数,防止分配过多造成系统内存不够
    if (ixc_mbuf_used_num >= IXC_MBUF_MAX)
        return NULL;

    m = malloc(sizeof(struct ixc_mbuf));
    if (NULL == m)
    {
        STDERR("no memory for struct ixc_mbuf\r\n");
        return NULL;
    }

    DBG("get mbuf from malloc\r\n");

    m->next = NULL;
    m->loop_trace = 0;

    ixc_mbuf_used_num += 1;

    return m;
}

static void __ixc_mbuf_put(struct ixc_mbuf *m)
{
    if (!ixc_mbuf_is_initialized)
    {
        STDERR("no initialized\r\n");
        return;
    }

    if (NULL == m)
        return;

    if (ixc_mbuf_used_num > ixc_mbuf_pre_alloc_num)
    {
        free(m);
        ixc_mbuf_used_num -= 1;
        DBG("mbuf free\r\n");
        return;
    }
    m->next = NULL;
    m->next = ixc_mbuf_empty_head;
    ixc_mbuf_empty_head = m;
}

static struct ixc_mbuf *__ixc_mbuf_clone(struct ixc_mbuf *m)
{
    struct ixc_mbuf *new_mbuf;

    if (NULL == m)
        return NULL;
    new_mbuf = ixc_mbuf_get();
    if (NULL == new_mbuf)
    {
        STDERR("cannot get mbuf for clone\r\n");
        return NULL;
    }

    new_mbuf->next = NULL;
    new_mbuf->is_ipv6 = m->is_ipv6;
    new_mbuf->begin = m->begin;
    new_mbuf->offset = m->offset;
    new_mbuf->tail = m->tail;
    new_mbuf->end = m->tail;
    new_mbuf->link_proto = m->link_proto;

    memcpy(new_mbuf->dst_hwaddr, m->dst_hwaddr, 6);
    memcpy(new_mbuf->src_hwaddr, m->src_hwaddr, 6);

    memcpy(new_mbuf->data + new_mbuf->begin, m->data + m->begin, m->end - m->begin);

    return new_mbuf;
}

struct ixc_mbuf *ixc_mbuf_get(void)
{
    struct ixc_mbuf *m=NULL;
    __ixc_mbuf_lock();
    m=__ixc_mbuf_get();
    __ixc_mbuf_unlock();

    return m;
}

void ixc_mbuf_put(struct ixc_mbuf *m)
{
    __ixc_mbuf_lock();
    __ixc_mbuf_put(m);
    __ixc_mbuf_unlock();
}

struct ixc_mbuf *ixc_mbuf_clone(struct ixc_mbuf *m)
{
    struct ixc_mbuf *new_m=NULL;
    __ixc_mbuf_lock();
    new_m=__ixc_mbuf_clone(m);
    __ixc_mbuf_unlock();

    return new_m;
}

void ixc_mbuf_puts(struct ixc_mbuf *m_head)
{
    struct ixc_mbuf *m=m_head,*t;
    __ixc_mbuf_lock();
    while(NULL!=m){
        t=m->next;
        __ixc_mbuf_put(m);
        m=t;
    }
    __ixc_mbuf_unlock();
}