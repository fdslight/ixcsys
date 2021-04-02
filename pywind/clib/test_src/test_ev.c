#include<stdio.h>

#include "../ev/ev.h"
#include "../ev/rpc.h"

static struct ev_set ev_set;


int main(int argc,char *arv[])
{
    int rs=ev_set_init(&ev_set,1);
    rs=rpc_create(&ev_set,"127.0.0.1",8889,0);

    printf("%d\r\n",rs);
    
    return 0;
}