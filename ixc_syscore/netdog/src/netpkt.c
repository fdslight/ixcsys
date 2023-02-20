#include <arpa/inet.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/un.h>
#include <time.h>
#include <pthread.h>
#include <signal.h>

#include "netpkt.h"
#include "netdog.h"

#include "./anylize/ether.h"
#include "./anylize/anylize_worker.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static int netpkt_is_initialized = 0;
static int netpkt_fd = -1;
static unsigned char netpkt_key[16];
static struct ev_set *netpkt_ev_set;
static struct ev *netpkt_ev;

struct ixc_mbuf *netpkt_sent_first=NULL;
struct ixc_mbuf *netpkt_sent_last=NULL;
// 等待处理的数据包
struct ixc_mbuf *wait_anylize_first=NULL;
struct ixc_mbuf *wait_anylize_last=NULL;

static int netpkt_add_writable=0;

/// 生成随机key
static void ixc_netpkt_gen_rand_key(void)
{
    int n;

    for (int i = 0; i < 4; i++)
    {
        srand((unsigned int)time(NULL));
        n = rand();

        memcpy(&netpkt_key[i*4],&n,4);
    }
}

// 分配给工作线程
static int ixc_netpkt_alloc_worker(struct ixc_mbuf *m)
{
    int v=0;
    struct ixc_ether_header *eth_header=(struct ixc_ether_header *)(m->data+m->begin);
    unsigned short *x=(unsigned short *)(eth_header->src_hwaddr);
    
    // 根据源MAC地址分配到相应线程
    for(int n=0;n<3;n++) v+=*x++;
    
    return v % ixc_netdog_worker_num_get();
}

/// @分配数据包到对应的worker
/// @param m 
/// @return 能够处理返回0,不能处理返回1,故障返回-1
static int ixc_netpkt_delivery_to_worker_handle(struct ixc_mbuf *m,int worker_seq)
{
    struct ixc_worker_context *ctx=ixc_anylize_worker_get(worker_seq);
    struct ixc_worker_mbuf_ring *ring=ctx->ring_last;
    
    if(NULL==ctx){
        STDERR("cannot get worker\r\n");
        ixc_mbuf_put(m);
        return -1;
    }

    m->next=NULL;

    if(ring->is_used){
        ring=ring->next;
        // 检查它的下一个mbuf是否在使用
        if(ring->is_used){
            STDERR("Work slowly\r\n");
            ixc_mbuf_put(m);
            return -1;
        }
        ring->npkt=m;
        ctx->ring_last=ring;
    }else{
        ring->npkt=m;
    }

    ring->is_used=1;

    return 0;
}

/// @投递任务
/// @param  
static void ixc_netpkt_delivery_task(void)
{
    struct ixc_mbuf *m,*t;
    struct ixc_worker_context *ctx;
    int v;

    m=wait_anylize_first;

    while(1){
        if(NULL==m) break;

        t=m->next;
        m->next=NULL;
        
        v=ixc_netpkt_alloc_worker(m);
        ixc_netpkt_delivery_to_worker_handle(m,v);
        m=t;
        STDERR("MA\r\n");
    }
    
    wait_anylize_first=NULL;
    wait_anylize_last=NULL;

    // 如果有线程需要唤醒,那么发送信号
    for(int n=0;n<IXC_WORKER_NUM_MAX;n++){
        ctx=ixc_anylize_worker_get(n);
        if(NULL==ctx) break;
        if(!ctx->is_working) pthread_kill(ctx->id,SIGUSR1);
    }

}

static void ixc_netpkt_handle(struct ixc_mbuf *m,struct sockaddr_in *from)
{
    struct ixc_netpkt_header *header=(struct ixc_netpkt_header *)(m->data+m->begin);
 
    // 检查key值是否匹配
    if(memcmp(header->key,netpkt_key,16)){
        ixc_mbuf_put(m);
        return;
    }
 
    // 检查端口
    if(from->sin_port!=htons(8964)){
        ixc_mbuf_put(m);
        return;
    }

    m->begin=m->offset+=sizeof(struct ixc_netpkt_header);
    m->next=NULL;

    if(NULL==wait_anylize_first){
        wait_anylize_first=m;
    }else{
        wait_anylize_last->next=m;
    }
    wait_anylize_last=m;
}

static int ixc_netpkt_rx_data(void)
{
    struct ixc_mbuf *m;
    ssize_t recv_size;
    struct sockaddr_in from;
    socklen_t fromlen;

    for (int n = 0; n < 16 * ixc_netdog_worker_num_get(); n++)
    {
        m = ixc_mbuf_get();
        if (NULL == m)
        {
            STDERR("cannot get mbuf\r\n");
            break;
        }

        recv_size = recvfrom(netpkt_fd, m->data + IXC_MBUF_BEGIN, IXC_MBUF_DATA_MAX_SIZE - IXC_MBUF_BEGIN, 0, &from, &fromlen);

        if (recv_size < 0)
        {
            ixc_mbuf_put(m);
            break;
        }

        // DBG_FLAGS;
        //  检查是否满足最小长度要求
        if (recv_size < sizeof(struct ixc_netpkt_header))
        {
            ixc_mbuf_put(m);
            continue;
        }

        // DBG_FLAGS;
        m->begin = IXC_MBUF_BEGIN;
        m->offset = IXC_MBUF_BEGIN;
        m->tail = IXC_MBUF_BEGIN + recv_size;
        m->end = m->tail;

        memcpy(m->from_addr,&from,sizeof(struct sockaddr_in));

        ixc_netpkt_handle(m,&from);
    }

    return 0;
}

static int ixc_netpkt_tx_data(void)
{
    struct ixc_mbuf *m = netpkt_sent_first, *t;
    ssize_t sent_size = 0;
    struct sockaddr_in *to_addr;
    socklen_t tolen = sizeof(struct sockaddr_in);

    while (NULL != m)
    {
        to_addr = (struct sockaddr_in *)(m->to_addr);
        sent_size = sendto(netpkt_fd, m->data + m->begin, m->end - m->begin, 0, to_addr, tolen);

        if (sent_size < 0)
        {
            netpkt_sent_first = m;
            if (EAGAIN != errno)
            {
                // 此处避免发生错误堆积过多数据包导致内存被使用完毕
                t = m->next;
                ixc_mbuf_put(m);
                m = t;
                netpkt_sent_first = m;
                STDERR("error for send netpkt data\r\n");
            }
            break;
        }

        t = m->next;
        ixc_mbuf_put(m);
        m = t;
    }

    if (NULL == m)
    {
        netpkt_sent_last = NULL;
        if (netpkt_add_writable)
        {
            ev_modify(netpkt_ev_set, netpkt_ev, EV_WRITABLE, EV_CTL_DEL);
            netpkt_add_writable = 0;
        }
    }
    return 0;
}

static int ixc_netpkt_readable_fn(struct ev *ev)
{
    ixc_netpkt_rx_data();
    return 0;
}

static int ixc_netpkt_writable_fn(struct ev *ev)
{
    ixc_netpkt_tx_data();
    return 0;
}

static int ixc_netpkt_timeout_fn(struct ev *ev)
{
    return 0;
}

static int ixc_netpkt_del_fn(struct ev *ev)
{
    close(ev->fileno);
    return 0;
}


int ixc_netpkt_init(struct ev_set *ev_set)
{
    int listenfd, rs;
    struct sockaddr_in in_addr;
    char buf[256];
    struct ev *ev;

    ixc_netpkt_gen_rand_key();

    listenfd = socket(AF_INET, SOCK_DGRAM, 0);

    if (listenfd < 0)
    {
        STDERR("cannot create netpkt socket fileno\r\n");
        return -1;
    }

    memset(&in_addr, '0', sizeof(struct sockaddr_in));

    in_addr.sin_family = AF_INET;
    inet_pton(AF_INET, "127.0.0.1", buf);

    memcpy(&(in_addr.sin_addr.s_addr), buf, 4);
    in_addr.sin_port = htons(0);

    rs = bind(listenfd, (struct sockaddr *)&in_addr, sizeof(struct sockaddr));

    if (rs < 0)
    {
        STDERR("cannot bind netpkt socket fileno\r\n");
        close(listenfd);

        return -1;
    }

    rs = ev_setnonblocking(listenfd);
    if (rs < 0)
    {
        close(listenfd);
        STDERR("cannot set nonblocking\r\n");
        return -1;
    }

    ev = ev_create(ev_set, listenfd);
    if (NULL == ev)
    {
        close(listenfd);
        STDERR("cannot create event for fd %d\r\n", listenfd);
        return -1;
    }

    if (ev_timeout_set(ev_set, ev, 10) < 0)
    {
        ev_delete(ev_set, ev);
        close(listenfd);
        STDERR("cannot set timeout for fd %d\r\n", listenfd);
        return -1;
    }

    EV_INIT_SET(ev, ixc_netpkt_readable_fn, ixc_netpkt_writable_fn, ixc_netpkt_timeout_fn, ixc_netpkt_del_fn, NULL);
    rs = ev_modify(ev_set, ev, EV_READABLE, EV_CTL_ADD);

    if (rs < 0)
    {
        ev_delete(ev_set, ev);
        STDERR("cannot add to readable for fd %d\r\n", listenfd);
        return -1;
    }

    netpkt_is_initialized = 1;
    netpkt_fd = listenfd;
    netpkt_ev_set = ev_set;
    netpkt_ev = ev;

    return 0;
}

void ixc_netpkt_uninit(void)
{
    if (netpkt_is_initialized)
        ev_delete(netpkt_ev_set, netpkt_ev);
        
    netpkt_is_initialized = 0;
}

// 获取通信端口
int ixc_netpkt_port_get(unsigned short *port)
{
    struct sockaddr_in addr;
    socklen_t socklen;

    if (netpkt_fd < 0)
        return -1;

    socklen = sizeof(addr);

    getsockname(netpkt_fd, (void *)&addr, &socklen);

    *port = addr.sin_port;

    return 0;
}

int ixc_netpkt_key_get(unsigned char *res)
{
    memcpy(res, netpkt_key, 16);

    return 0;
}

void ixc_netpkt_send(struct ixc_mbuf *m)
{
    m->next=NULL;
    if (NULL == netpkt_sent_first)
    {
        netpkt_sent_first = m;
    }
    else
    {
        netpkt_sent_last->next = m;
    }
    netpkt_sent_last = m;

    if (!netpkt_add_writable)
    {
        ev_modify(netpkt_ev_set, netpkt_ev, EV_WRITABLE, EV_CTL_ADD);
        netpkt_add_writable = 1;
    }
}

int ixc_netpkt_have(void)
{
    struct ixc_worker_context *ctx;
    // 如果有线程需要唤醒,那么发送信号
    for(int n=0;n<IXC_WORKER_NUM_MAX;n++){
        ctx=ixc_anylize_worker_get(n);
        if(NULL==ctx) break;
        if(!ctx->is_working && ctx->ring_last->is_used) return 1;
    }

    if(NULL==wait_anylize_first) return 0;
    return 1;
}

void ixc_netpkt_loop(void)
{
    ixc_netpkt_delivery_task();
}