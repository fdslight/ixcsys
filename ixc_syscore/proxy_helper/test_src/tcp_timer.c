#include<stdio.h>
#include<time.h>
#include<unistd.h>

#include "../src/tcp_timer.h"



void cb_fn(void *session)
{
    printf("timeout\r\n");
}

int main(int argc,char *arv[])
{
    struct tcp_timer_node *node;
    int rs=tcp_timer_init(20,100);
    
    node=tcp_timer_add(400,cb_fn,NULL);
    node->is_valid=1;

    tcp_timer_do();
    //sleep(0);
    
    printf("%d\r\n",rs);
    //tcp_timer_do();
    tcp_timer_uninit();

    return 0;
}