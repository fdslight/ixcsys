#include<stdio.h>
#include<stdlib.h>
#include<unistd.h>

#include "../timer.h"
#include "../debug.h"

 

static void timeout_fn(void *data)
{
    DBG("hello,world\r\n");
}

int main(int argc,char *argv[])
{
    struct time_wheel wheel;
    int rs=time_wheel_new(&wheel,60,1,timeout_fn,16);
    struct time_data *tdata=time_wheel_add(&wheel,NULL,1);

    sleep(1);

    //printf("%d\r\n",rs);

    time_wheel_handle(&wheel);
    time_wheel_handle(&wheel);


    return 0;
}