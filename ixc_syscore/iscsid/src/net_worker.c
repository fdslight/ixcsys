#include<stdio.h>
#include<stdlib.h>
#include<unistd.h>
#include<string.h>
#include<errno.h>

#include "net_worker.h"
#include "mbuf.h"

#include "iscsi/session.h"

#include "../../../pywind/clib/debug.h"

static int iscsi_client_fd=-1;

struct ev_set iscsi_ev_set;
struct ev *iscsi_ev;

static struct sockaddr iscsi_client_addr;
static socklen_t iscsi_client_addrlen;
static int iscsi_session_is_ipv6;

static struct ixc_mbuf *sent_last=NULL;
static struct ixc_mbuf *sent_first=NULL;
// 是否已经加入可读
static int is_added_writable=0;
// 是否发生故障
static int iscsi_is_err=0;

static int ixc_iscsid_readable_fn(struct ev *ev)
{
    struct ixc_mbuf *m;
    ssize_t recv_size;

    for(int i=0;i<10;i++){
        if(iscsi_is_err) break;
        m=ixc_mbuf_get();
        if(NULL==m){
            STDERR("cannot get mbuf\r\n");
            break;
        }

        m->begin=IXC_MBUF_BEGIN;
        
        recv_size=recv(iscsi_client_fd,m->data+m->begin,IXC_MBUF_DATA_MAX_SIZE-m->begin,0);
        if(0==recv_size){
            iscsi_is_err=1;
            return -1;
        }
        if(recv_size<0){
            if(EAGAIN==errno){
                ixc_mbuf_put(m);
                break;
            }
            ixc_mbuf_put(m);
            iscsi_is_err=1;
            return -1;
        }
        iscsi_is_err= ixc_iscsi_session_handle_request(m);
        if(iscsi_is_err) break;
    }
    return iscsi_is_err;
}

static int ixc_iscsid_writable_fn(struct ev *ev)
{
    struct ixc_mbuf *t;
    ssize_t sent_size;
    int blk_wsize;

    if(NULL==sent_first){
        is_added_writable=0;
        ev_modify(&iscsi_ev_set,iscsi_ev,EV_WRITABLE,EV_CTL_DEL);
        return 0;
    }

    while(1){
        t=sent_first;
        if(NULL==t) break;

        blk_wsize=t->end-t->begin;
        
        if(blk_wsize>4096) blk_wsize=4096;
    
        sent_size=send(iscsi_client_fd,t->data+t->begin,blk_wsize,0);
        if(sent_size<0){
            if(EAGAIN!=errno) return -1;
            iscsi_is_err=1;
            break;
        }

        t->begin+=sent_size;

        if(0==t->end-t->begin){
            sent_first=t->next;
            if(NULL==sent_first) sent_last=NULL;
        }
    }

    return 0;
}

static int ixc_iscsid_timeout_fn(struct ev *ev)
{
    return 0;
}

static int ixc_iscsid_del_fn(struct ev *ev)
{
    close(ev->fileno);
    iscsi_is_err=1;
    return 0;
}

static void ixc_iscsi_stop(void)
{
    struct ixc_mbuf *t;
    
    while(NULL!=sent_first){
        t=sent_first->next;
        free(sent_first);
        sent_first=t;
    }

    ixc_mbuf_uninit();
    exit(EXIT_SUCCESS);
}

static void myloop(void)
{
    if(iscsi_is_err){
        ixc_iscsi_stop();
    }
}

int ixc_net_worker_start(int client_fd,struct sockaddr *client_addr,socklen_t client_addrlen,int is_ipv6)
{
    struct ev *ev;
    int rs;

    iscsi_client_fd=client_fd;
    iscsi_session_is_ipv6=is_ipv6;
    iscsi_client_addrlen=client_addrlen;
    is_added_writable=0;
    
    memcpy(&iscsi_client_addr,client_addr,client_addrlen);

    sent_first=NULL;
    sent_last=NULL;
    iscsi_is_err=0;

    rs=ixc_mbuf_init(32);

    if(rs<0){
        close(client_fd);
        STDERR("cannot init mbuf\r\n");
        return -1;
    }

    rs=ev_set_init(&iscsi_ev_set,0);

    if(rs<0){
        ixc_mbuf_uninit();
        STDERR("cannot init ev_set\r\n");
        close(client_fd);

        return -1;
    }

    ev=ev_create(&iscsi_ev_set,client_fd);
    if(NULL==ev){
        ixc_mbuf_uninit();
        ev_set_uninit(&iscsi_ev_set);
		close(client_fd);
		STDERR("cannot create event for fd %d\r\n",client_fd);
		return -1;
	}

    if(ev_timeout_set(&iscsi_ev_set,ev,10)<0){
        ixc_mbuf_uninit();
        ev_delete(&iscsi_ev_set,ev);
        ev_set_uninit(&iscsi_ev_set);
        close(client_fd);
		STDERR("cannot set timeout for fd %d\r\n",client_fd);
        return -1;
	}

	EV_INIT_SET(ev,ixc_iscsid_readable_fn,ixc_iscsid_writable_fn,ixc_iscsid_timeout_fn,ixc_iscsid_del_fn,NULL);
	rs=ev_modify(&iscsi_ev_set,ev,EV_READABLE,EV_CTL_ADD);

	if(rs<0){
        ixc_mbuf_uninit();
		ev_delete(&iscsi_ev_set,ev);
        ev_set_uninit(&iscsi_ev_set);
		STDERR("cannot add to readablefor fd %d\r\n",client_fd);
		return -1;
	}

    ev_setnonblocking(client_fd);
    ev_modify(&iscsi_ev_set,ev,EV_READABLE,EV_CTL_ADD);

    iscsi_ev=ev;
    iscsi_ev_set.wait_timeout=10;
    iscsi_ev_set.myloop_fn=myloop;

    if(ixc_iscsi_session_init()<0){
        ev_delete(&iscsi_ev_set,ev);
        ev_set_uninit(&iscsi_ev_set);
        ixc_mbuf_uninit();
        STDERR("cannot init iscsi session\r\n");
        return -1;
    }
    
    return rs;
}

void ixc_net_worker_evloop(void)
{
    ev_loop(&iscsi_ev_set);
}

void ixc_net_worker_send(struct ixc_mbuf *m)
{
    m->next=NULL;

    if(NULL==sent_first){
        sent_first=m;
    }else{
        sent_last->next=m;
    }

    sent_last=m;

    if(!is_added_writable){
        ev_modify(&iscsi_ev_set,iscsi_ev,EV_WRITABLE,EV_CTL_ADD);
    }
}

void ixc_net_worker_close(void)
{
    ev_delete(&iscsi_ev_set,iscsi_ev);
    iscsi_is_err=1;
}