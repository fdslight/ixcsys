#include<stdio.h>
#include<time.h>
#include<unistd.h>

#include "../src/tcp_timer.h"

struct x{
    struct tcp_timer_node *node;
};

void cb_fn(void *data)
{
    struct x *t=data;

    tcp_timer_update(t->node,900);

    printf("timeout\r\n");
}

int main(int argc,char *arv[])
{
    struct x t;
    struct tcp_timer_node *node;
    int rs=tcp_timer_init(20,100);
    
    node=tcp_timer_add(400,cb_fn,&t);
    t.node=node;

    tcp_timer_do();
    //sleep(1);
    tcp_timer_do();

    
    printf("%d\r\n",rs);
    //tcp_timer_do();
    //tcp_timer_uninit();

    return 0;
}