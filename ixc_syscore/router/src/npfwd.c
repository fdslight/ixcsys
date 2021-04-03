#include<arpa/inet.h>
#include<unistd.h>
#include<string.h>

#include "npfwd.h"

#include "../../../pywind/clib/debug.h"

#include "../../../pywind/clib/ev/ev.h"

static struct ixc_npfwd npfwd;
static struct ixc_npfwd_info npfwd_info[IXC_NPFWD_INFO_MAX];

static struct ixc_mbuf *npfwd_mbuf_first=NULL;
static struct ixc_mbuf *npfwd_mbuf_last=NULL;

static void ixc_npfwd_rx_data(void)
{
    struct ixc_mbuf *m;

    for(int n=0;n<10;n++){

    }
}

static void ixc_npfwd_tx_data(void)
{
    struct ixc_mbuf *m=npfwd_mbuf_first;
}

static int ixc_npfwd_readable_fn(struct ev *ev)
{
    ixc_npfwd_rx_data();

    return 0;
}

static int ixc_npfwd_writable_fn(struct ev *ev)
{
    ixc_npfwd_tx_data();

    // 如果数据已经发送完毕那么移除写事件
    if(NULL==npfwd_mbuf_first){
        ev_modify(npfwd.ev_set,ev,EV_WRITABLE,EV_CTL_DEL);
    }

    return 0;
}

static int ixc_npfwd_timeout_fn(struct ev *ev)
{
    return 0;
}

static int ixc_npfwd_del_fn(struct ev *ev)
{
    return 0;
}

int ixc_npfwd_init(struct ev_set *ev_set)
{
    int listenfd,rs;
    struct sockaddr_in in_addr;
    char buf[256];
    struct ev *ev;

    bzero(npfwd_info,sizeof(struct ixc_npfwd_info)*IXC_NPFWD_INFO_MAX);

    listenfd=socket(AF_INET,SOCK_DGRAM,0);

    if(listenfd<0){
        STDERR("cannot create socket fileno\r\n");
        return -1;
    }

    memset(&in_addr,'0',sizeof(struct sockaddr_in));

    in_addr.sin_family=AF_INET;

    memcpy(&(in_addr.sin_addr.s_addr),buf,4);
	in_addr.sin_port=htons(8964);

    inet_pton(AF_INET,"127.0.0.1",buf);
    rs=bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct sockaddr));

    if(rs<0){
        STDERR("cannot bind npfwd\r\n");
        close(listenfd);

        return -1;
    }

    rs=ev_setnonblocking(listenfd);
	if(rs<0){
		close(listenfd);
		STDERR("cannot set nonblocking\r\n");
		return -1;
	}

    npfwd.fileno=listenfd;
    npfwd.ev_set=ev_set;

    ev=ev_create(ev_set,listenfd);
    if(NULL==ev){
		close(listenfd);
		STDERR("cannot create event for fd %d\r\n",listenfd);
		return -1;
	}

    if(ev_timeout_set(ev_set,ev,10)<0){
		STDERR("cannot set timeout for fd %d\r\n",listenfd);
        return -1;
	}

	EV_INIT_SET(ev,ixc_npfwd_readable_fn,ixc_npfwd_writable_fn,ixc_npfwd_timeout_fn,ixc_npfwd_del_fn,&npfwd);
	rs=ev_modify(ev_set,ev,EV_READABLE,EV_CTL_ADD);

	if(rs<0){
		ev_delete(ev_set,ev);
		STDERR("cannot add to readablefor fd %d\r\n",listenfd);
		return -1;
	}

    return 0;
}

void ixc_npfwd_uninit(void)
{

}

int ixc_npfwd_send_raw(struct ixc_mbuf *m,unsigned char ipproto,unsigned char flags)
{
    unsigned char *s=NULL;
    if(NULL==m) return 0;

    s=(unsigned char *)(&m->priv_flags);

    s[0]=ipproto;
    s[1]=flags;

    m->next=NULL;

    if(NULL==npfwd_mbuf_first){
        npfwd_mbuf_first=m;
    }else{
        npfwd_mbuf_last->next=m;
    }

    npfwd_mbuf_last=m;

    return 0;
}

int ixc_npfwd_set_forward(unsigned char *key,unsigned short port)
{
    return 0;
}