#include<stdio.h>

#include "../ev/ev.h"
#include "../ev/rpc.h"

static struct ev_set ixc_ev_set;

int main(int argc,char *arv[])
{
    int rs=ev_set_init(&ixc_ev_set,1);
    rs=rpc_create(&ixc_ev_set,"127.0.0.1",1999,0);

    rs=ev_loop(&ixc_ev_set);

    
    return 0;
}