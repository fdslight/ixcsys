#include<stdio.h>
#include<time.h>
#include<unistd.h>
#include<sys/time.h>

#include "../src/tcp_timer.h"

struct x{
    struct tcp_timer_node *node;
    int id;
};

void cb_fn(void *data)
{
    struct x *t=data;

    printf("id %d timeout\r\n",t->id);
}

int main(int argc,char *arv[])
{
    struct x t1,t2;
    //struct timeval v1,v2;
    struct tcp_timer_node *node;
    int rs=tcp_timer_init(20,100);
    
    node=tcp_timer_add(400,cb_fn,&t1);
    t1.node=node;
    t1.id=0;

    node=tcp_timer_add(1000,cb_fn,&t2);
    t2.node=node;
    t2.id=1;

    sleep(1);

    tcp_timer_do();
    tcp_timer_do();

    

    //gettimeofday(&v1,NULL);
    //sleep(1);
    //gettimeofday(&v2,NULL);

    //printf("%d %ld\r\n",rs,tcp_timer_interval_calc(&v1,&v2));

    //tcp_timer_do();
    //tcp_timer_uninit();

    return 0;
}