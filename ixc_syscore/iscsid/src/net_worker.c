#include<stdio.h>
#include<stdlib.h>
#include<unistd.h>
#include<string.h>

#include "net_worker.h"

#include "../../../pywind/clib/debug.h"

static int iscsi_client_fd=-1;

struct ev_set iscsi_ev_set;
struct ev *iscsi_ev;

static struct sockaddr iscsi_client_addr;
static socklen_t iscsi_client_addrlen;
static int iscsi_session_is_ipv6;

static int ixc_iscsid_readable_fn(struct ev *ev)
{
    STDOUT("hello\r\n");

    return 0;
}

static int ixc_iscsid_writable_fn(struct ev *ev)
{
    return 0;
}

static int ixc_iscsid_timeout_fn(struct ev *ev)
{
    return 0;
}

static int ixc_iscsid_del_fn(struct ev *ev)
{
    close(ev->fileno);
    return 0;
}

int ixc_net_worker_start(int client_fd,struct sockaddr *client_addr,socklen_t client_addrlen,int is_ipv6)
{
    struct ev *ev;
    int rs;

    iscsi_client_fd=client_fd;
    iscsi_session_is_ipv6=is_ipv6;
    iscsi_client_addrlen=client_addrlen;
    
    memcpy(&iscsi_client_addr,client_addr,client_addrlen);

    rs=ev_set_init(&iscsi_ev_set,0);

    if(rs<0){
        STDERR("cannot init ev_set\r\n");
        close(client_fd);

        return -1;
    }

    ev=ev_create(&iscsi_ev_set,client_fd);
    if(NULL==ev){
		close(client_fd);
		STDERR("cannot create event for fd %d\r\n",client_fd);
		return -1;
	}

    if(ev_timeout_set(&iscsi_ev_set,ev,10)<0){
        ev_delete(&iscsi_ev_set,ev);
        close(client_fd);
		STDERR("cannot set timeout for fd %d\r\n",client_fd);
        return -1;
	}

	EV_INIT_SET(ev,ixc_iscsid_readable_fn,ixc_iscsid_writable_fn,ixc_iscsid_timeout_fn,ixc_iscsid_del_fn,NULL);
	rs=ev_modify(&iscsi_ev_set,ev,EV_READABLE,EV_CTL_ADD);

	if(rs<0){
		ev_delete(&iscsi_ev_set,ev);
		STDERR("cannot add to readablefor fd %d\r\n",client_fd);
		return -1;
	}

    ev_setnonblocking(client_fd);
    ev_modify(&iscsi_ev_set,ev,EV_READABLE,EV_CTL_ADD);

    iscsi_ev=ev;
    
    return rs;
}

void ixc_net_worker_evloop(void)
{
    ev_loop(&iscsi_ev_set);
}