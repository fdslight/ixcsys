#include <arpa/inet.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/un.h>
#include <time.h>

#include "netpkt_recv.h"

#include "../../../pywind/clib/debug.h"

static int netpkt_recv_is_initialized = 0;
static int netpkt_recv_fd = -1;
static unsigned char netpkt_recv_key[16];

/// 生成随机key
static void ixc_netpkt_gen_rand_key(void)
{
    int n;
    unsigned char ch;

    for(int i=0;i<16;i++){
        srand((unsigned int)time(NULL));
        n = rand();

        ch = n % 0xff;
        netpkt_recv_key[i]=ch;
    }
}

static int ixc_netpkt_recv_readable_fn(struct ev *ev)
{
    return 0;
}

static int ixc_netpkt_recv_writable_fn(struct ev *ev)
{
    return 0;
}

static int ixc_netpkt_recv_timeout_fn(struct ev *ev)
{
    return 0;
}

static int ixc_netpkt_recv_del_fn(struct ev *ev)
{
    close(ev->fileno);
    return 0;
}

int ixc_netpkt_recv_init(struct ev_set *ev_set)
{
    int listenfd, rs;
    struct sockaddr_in in_addr;
    char buf[256];
    struct ev *ev;

    ixc_netpkt_gen_rand_key();
    
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
    in_addr.sin_port = htons(0);

    rs = bind(listenfd, (struct sockaddr *)&in_addr, sizeof(struct sockaddr));

    if (rs < 0)
    {
        STDERR("cannot bind netpkt_recv socket fileno\r\n");
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

    EV_INIT_SET(ev, ixc_netpkt_recv_readable_fn, ixc_netpkt_recv_writable_fn, ixc_netpkt_recv_timeout_fn, ixc_netpkt_recv_del_fn, NULL);
    rs = ev_modify(ev_set, ev, EV_READABLE, EV_CTL_ADD);

    if (rs < 0)
    {
        ev_delete(ev_set, ev);
        STDERR("cannot add to readable for fd %d\r\n", listenfd);
        return -1;
    }

    netpkt_recv_is_initialized = 1;
    netpkt_recv_fd = listenfd;
    

    return 0;
}

void ixc_netpkt_recv_uninit(void)
{
    netpkt_recv_is_initialized = 0;
}

// 获取通信端口
int ixc_netpkt_recv_port_get(unsigned short *port)
{
    struct sockaddr_in addr;
    socklen_t socklen;

    if (netpkt_recv_fd < 0)
        return -1;

    socklen = sizeof(addr);

    getsockname(netpkt_recv_fd, (void *)&addr, &socklen);

    *port = addr.sin_port;

    return 0;
}

int ixc_netpkt_recv_key_get(unsigned char *res)
{
    memcpy(res, netpkt_recv_key, 16);

    return 0;
}