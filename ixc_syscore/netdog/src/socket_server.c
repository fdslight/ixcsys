

#include "socket_server.h"
#include "netpkt_recv.h"
#include "sys_msg.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/ev/ev.h"

static struct ev_set ixc_socket_ev_set;


int ixc_socket_server_init(void)
{
    int rs;
    rs=ev_set_init(&ixc_socket_ev_set,0);

    if(rs<0){
        STDERR("cannot init event set\r\n");
        return -1;
    }

    rs=ixc_netpkt_recv_init(&ixc_socket_ev_set);
    rs=ixc_sys_msg_init(&ixc_socket_ev_set);

    return 0;
}

void ixc_socket_server_uninit(void)
{
    ixc_netpkt_recv_uninit();
    ixc_sys_msg_uninit();
}

void ixc_socket_server_ioloop(void)
{
    ev_loop(&ixc_socket_ev_set);
}