#include<arpa/inet.h>
#include<unistd.h>
#include<string.h>
#include<errno.h>
#include<sys/un.h>

#include "sys_msg.h"
#include "netpkt_recv.h"
#include "mbuf.h"

#include "../../../pywind/clib/debug.h"

static int sys_msg_is_initialized=0;
static int sys_msg_fd=-1;


static void __ixc_sys_msg_handle_port_req(void)
{
    unsigned short port;
    ixc_netpkt_recv_port_get(&port);
    ixc_sys_msg_send(IXC_SYS_MSG_RPC_RESP_PKT_MON_PORT,&port,sizeof(unsigned short));
}

static void __ixc_sys_msg_handle(struct ixc_mbuf *m)
{
    struct ixc_sys_msg *sys_msg=(struct ixc_sys_msg *)(m->data+m->begin);

    switch (sys_msg->type){
        case IXC_SYS_MSG_RPC_REQ_PKT_MON_PORT:
            __ixc_sys_msg_handle_port_req();
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

    for(int n=0;n<10;n++){
        m=ixc_mbuf_get();
        if(NULL==m){
            STDERR("cannot get mbuf\r\n");
            break;
        }

        recv_size=recvfrom(sys_msg_fd,m->data+IXC_MBUF_BEGIN,IXC_MBUF_DATA_MAX_SIZE-IXC_MBUF_BEGIN,0,&from,&fromlen);

        if(recv_size<0){
            ixc_mbuf_put(m);
            break;
        }

        //DBG_FLAGS;
        // 检查是否满足最小长度要求
        if(recv_size<sizeof(struct ixc_sys_msg)){
            ixc_mbuf_put(m);
            continue;
        }

        //DBG_FLAGS;
        m->begin=IXC_MBUF_BEGIN;
        m->offset=IXC_MBUF_BEGIN;
        m->tail=IXC_MBUF_BEGIN+recv_size;
        m->end=m->tail;

        __ixc_sys_msg_handle(m);
    }

    return 0;
}

static void __ixc_sys_msg_tx_data(void)
{
    while(1){
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
  int listenfd,rs;
    struct sockaddr_in in_addr;
    char buf[256];
    struct ev *ev;

    listenfd=socket(AF_INET,SOCK_DGRAM,0);

    if(listenfd<0){
        STDERR("cannot create netpkt_recv socket fileno\r\n");
        return -1;
    }

    memset(&in_addr,'0',sizeof(struct sockaddr_in));

    in_addr.sin_family=AF_INET;
    inet_pton(AF_INET,"127.0.0.1",buf);

    memcpy(&(in_addr.sin_addr.s_addr),buf,4);
	in_addr.sin_port=htons(8965);

    rs=bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct sockaddr));

    if(rs<0){
        STDERR("cannot bind sys_msg socket fileno\r\n");
        close(listenfd);

        return -1;
    }

    rs=ev_setnonblocking(listenfd);
	if(rs<0){
		close(listenfd);
		STDERR("cannot set nonblocking\r\n");
		return -1;
	}

    ev=ev_create(ev_set,listenfd);
    if(NULL==ev){
		close(listenfd);
		STDERR("cannot create event for fd %d\r\n",listenfd);
		return -1;
	}

    if(ev_timeout_set(ev_set,ev,10)<0){
        ev_delete(ev_set,ev);
        close(listenfd);
		STDERR("cannot set timeout for fd %d\r\n",listenfd);
        return -1;
	}

	EV_INIT_SET(ev,ixc_sys_msg_readable_fn,ixc_sys_msg_writable_fn,ixc_sys_msg_timeout_fn,ixc_sys_msg_del_fn,NULL);
	rs=ev_modify(ev_set,ev,EV_READABLE,EV_CTL_ADD);

	if(rs<0){
		ev_delete(ev_set,ev);
		STDERR("cannot add to readable for fd %d\r\n",listenfd);
		return -1;
	}

    sys_msg_is_initialized=1;
    sys_msg_fd=listenfd;

    return 0;
}

void ixc_sys_msg_uninit(void)
{
    sys_msg_is_initialized=0;
}

int ixc_sys_msg_send(unsigned char type,void *data,size_t size)
{
    return 0;
}