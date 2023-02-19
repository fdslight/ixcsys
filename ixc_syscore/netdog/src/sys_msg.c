#include <arpa/inet.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/un.h>

#include "sys_msg.h"
#include "netpkt_recv.h"
#include "mbuf.h"

#include "../../../pywind/clib/debug.h"

static int sys_msg_is_initialized = 0;
static int sys_msg_fd = -1;

static struct ixc_mbuf *sys_msg_sent_first=NULL;
static struct ixc_mbuf *sys_msg_sent_last=NULL;
static int sys_msg_add_wriable=0;
static struct ev_set *sys_msg_ev_set=NULL;
static struct ev *sys_msg_ev=NULL;

static void __ixc_sys_msg_handle_port_req(struct sockaddr_in *to_addr)
{
    unsigned char buf[18];

    ixc_netpkt_recv_key_get(buf);
    ixc_netpkt_recv_port_get((unsigned short *)(buf + 16));

    ixc_sys_msg_send(IXC_SYS_MSG_RPC_RESP_PKT_MON_PORT, buf, 18,to_addr);
}

static void __ixc_sys_msg_handle(struct ixc_mbuf *m,struct sockaddr_in *from_addr)
{
    struct ixc_sys_msg *sys_msg = (struct ixc_sys_msg *)(m->data + m->begin);

    switch (sys_msg->type)
    {
    case IXC_SYS_MSG_RPC_REQ_PKT_MON_PORT:
        __ixc_sys_msg_handle_port_req(from_addr);
        ixc_mbuf_put(m);
        break;
    case IXC_SYS_MSG_ADD_RULE:
        ixc_mbuf_put(m);
        break;
    case IXC_SYS_MSG_DEL_RULE:
        ixc_mbuf_put(m);
        break;
    default:
        ixc_mbuf_put(m);
        break;
    }
}

static int __ixc_sys_msg_rx_data(void)
{
    struct ixc_mbuf *m;
    ssize_t recv_size;
    struct sockaddr from;
    socklen_t fromlen;

    for (int n = 0; n < 10; n++)
    {
        m = ixc_mbuf_get();
        if (NULL == m)
        {
            STDERR("cannot get mbuf\r\n");
            break;
        }

        recv_size = recvfrom(sys_msg_fd, m->data + IXC_MBUF_BEGIN, IXC_MBUF_DATA_MAX_SIZE - IXC_MBUF_BEGIN, 0, &from, &fromlen);

        if (recv_size < 0)
        {
            ixc_mbuf_put(m);
            break;
        }

        // DBG_FLAGS;
        //  检查是否满足最小长度要求
        if (recv_size < sizeof(struct ixc_sys_msg))
        {
            ixc_mbuf_put(m);
            continue;
        }

        // DBG_FLAGS;
        m->begin = IXC_MBUF_BEGIN;
        m->offset = IXC_MBUF_BEGIN;
        m->tail = IXC_MBUF_BEGIN + recv_size;
        m->end = m->tail;

        __ixc_sys_msg_handle(m,(struct sockaddr_in *)&from);
    }

    return 0;
}

static void __ixc_sys_msg_tx_data(void)
{
    struct ixc_mbuf *m=sys_msg_sent_first,*t;
    ssize_t sent_size=0;
    struct sockaddr_in *to_addr;
    socklen_t tolen=sizeof(struct sockaddr_in);

    while(NULL!=m){
        to_addr=(struct sockaddr_in *)(m->to_addr);
        sent_size=sendto(sys_msg_fd,m->data+m->begin,m->end-m->begin,0,to_addr,tolen);
        
        if(sent_size<0){
            sys_msg_sent_first=m;
            if(EAGAIN!=errno){
                // 此处避免发生错误堆积过多数据包导致内存被使用完毕
                t=m->next;
                ixc_mbuf_put(m);
                m=t;
                sys_msg_sent_first=m;
                STDERR("error for send sys_msg data\r\n");
            }
            break;
        }

        t=m->next;
        ixc_mbuf_put(m);
        m=t;
    }

    if(NULL==m){
        sys_msg_sent_last=NULL;
        if(sys_msg_add_wriable){
            ev_modify(sys_msg_ev_set,sys_msg_ev,EV_WRITABLE,EV_CTL_DEL);
            sys_msg_add_wriable=0;
        }
    }
}

static int ixc_sys_msg_readable_fn(struct ev *ev)
{

    __ixc_sys_msg_rx_data();

    return 0;
}

static int ixc_sys_msg_writable_fn(struct ev *ev)
{
    __ixc_sys_msg_tx_data();

    return 0;
}

static int ixc_sys_msg_timeout_fn(struct ev *ev)
{
    return 0;
}

static int ixc_sys_msg_del_fn(struct ev *ev)
{
    close(ev->fileno);
    return 0;
}

int ixc_sys_msg_init(struct ev_set *ev_set)
{
    int listenfd, rs;
    struct sockaddr_in in_addr;
    char buf[256];
    struct ev *ev;

    sys_msg_sent_first=NULL;
    sys_msg_sent_last=NULL;
    sys_msg_add_wriable=0;
    sys_msg_ev_set=ev_set;
    

    listenfd = socket(AF_INET, SOCK_DGRAM, 0);

    if (listenfd < 0)
    {
        STDERR("cannot create netpkt_recv socket fileno\r\n");
        return -1;
    }

    memset(&in_addr, '0', sizeof(struct sockaddr_in));

    in_addr.sin_family = AF_INET;
    inet_pton(AF_INET, "127.0.0.1", buf);

    memcpy(&(in_addr.sin_addr.s_addr), buf, 4);
    in_addr.sin_port = htons(8965);

    rs = bind(listenfd, (struct sockaddr *)&in_addr, sizeof(struct sockaddr));

    if (rs < 0)
    {
        STDERR("cannot bind sys_msg socket fileno\r\n");
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

    EV_INIT_SET(ev, ixc_sys_msg_readable_fn, ixc_sys_msg_writable_fn, ixc_sys_msg_timeout_fn, ixc_sys_msg_del_fn, NULL);
    rs = ev_modify(ev_set, ev, EV_READABLE, EV_CTL_ADD);

    if (rs < 0)
    {
        ev_delete(ev_set, ev);
        STDERR("cannot add to readable for fd %d\r\n", listenfd);
        return -1;
    }

    sys_msg_is_initialized = 1;
    sys_msg_fd = listenfd;
    sys_msg_ev=ev;

    return 0;
}

void ixc_sys_msg_uninit(void)
{
    sys_msg_is_initialized = 0;
}

int ixc_sys_msg_send(unsigned char type, void *data, unsigned short size,struct sockaddr_in *to_addr)
{
    struct ixc_mbuf *m=ixc_mbuf_get();
    struct ixc_sys_msg *msg_header;

    if(NULL==m) return -1;

    m->next=NULL;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=m->begin;
    m->tail=m->end=m->begin+size+sizeof(struct ixc_sys_msg);

    msg_header=(struct ixc_sys_msg *)(m->data+m->begin);
    msg_header->version=1;
    msg_header->type=type;
    
    memcpy(m->data+m->begin+sizeof(struct ixc_sys_msg),data,size);
    memcpy(m->to_addr,to_addr,sizeof(struct sockaddr_in));

    if(NULL==sys_msg_sent_first){
        sys_msg_sent_first=m;
    }else{
        sys_msg_sent_last->next=m;
    }
    sys_msg_sent_last=m;

    if(!sys_msg_add_wriable){
        ev_modify(sys_msg_ev_set,sys_msg_ev,EV_WRITABLE,EV_CTL_ADD);
        sys_msg_add_wriable=1;
    }

    return 0;
}