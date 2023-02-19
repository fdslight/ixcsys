#include "socket_server.h"
#include "netpkt.h"
#include "sys_msg.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/ev/ev.h"

static struct ev_set ixc_socket_ev_set;

static void ixc_socket_server_myloop(void)
{    
    if(ixc_netpkt_have()){
        ixc_netpkt_loop();
        ixc_socket_ev_set.wait_timeout=0;
    }else{
        ixc_socket_ev_set.wait_timeout=10;
    }
}

int ixc_socket_server_init(void)
{
    int rs;
    rs=ev_set_init(&ixc_socket_ev_set,0);

    if(rs<0){
        STDERR("cannot init event set\r\n");
        return -1;
    }
    rs=ixc_mbuf_init(256);

    if(rs<0){
        STDERR("cannot init mbuf\r\n");
        return -1;
    }

    rs=ixc_netpkt_init(&ixc_socket_ev_set);
    rs=ixc_sys_msg_init(&ixc_socket_ev_set);

    ixc_socket_ev_set.myloop_fn=ixc_socket_server_myloop;

    return 0;
}

void ixc_socket_server_uninit(void)
{
    ixc_netpkt_uninit();
    ixc_sys_msg_uninit();
    ixc_mbuf_uninit();
}

void ixc_socket_server_ioloop(void)
{
    ev_loop(&ixc_socket_ev_set);
}