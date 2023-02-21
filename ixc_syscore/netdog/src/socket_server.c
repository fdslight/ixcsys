#include "socket_server.h"
#include "netpkt.h"
#include "netdog.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/ev/ev.h"
#include "../../../pywind/clib/sysloop.h"

static struct ev_set ixc_socket_ev_set;

static void ixc_socket_server_myloop(void)
{ 
    sysloop_do();

    ixc_netpkt_loop();
    ixc_netdog_python_loop();
    ixc_socket_ev_set.wait_timeout=10;
}

int ixc_socket_server_init(void)
{
    int rs;
    rs=ev_set_init(&ixc_socket_ev_set,0);

    if(rs<0){
        STDERR("cannot init event set\r\n");
        return -1;
    }

    rs=sysloop_init();

    if(rs<0){
        STDERR("cannot init sysloop\r\n");
        return -1;
    }

    rs=ixc_mbuf_init(256);

    if(rs<0){
        STDERR("cannot init mbuf\r\n");
        return -1;
    }

    rs=ixc_netpkt_init(&ixc_socket_ev_set);
    if(rs<0){
        STDERR("cannot init netpkt\r\n");
        return -1;
    }
    

    ixc_socket_ev_set.myloop_fn=ixc_socket_server_myloop;

    return 0;
}

void ixc_socket_server_uninit(void)
{
    ixc_netpkt_uninit();
    ixc_mbuf_uninit();
    
    sysloop_uninit();
}

void ixc_socket_server_ioloop(void)
{
    ev_loop(&ixc_socket_ev_set);
}