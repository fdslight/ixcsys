#include<stdio.h>
#include<stdlib.h>
#include<unistd.h>

#include "../timer.h"
#include "../debug.h"

 
   struct time_wheel wheel;
static void timeout_fn(void *data)
{
    struct time_data *x;

    x=time_wheel_add(&wheel,data,2);

    DBG("hello,world\r\n");
}

int main(int argc,char *argv[])
{
 
    int rs=time_wheel_new(&wheel,60,2,timeout_fn,16);
    struct time_data *tdata=time_wheel_add(&wheel,NULL,1);

    sleep(2);

    printf("%d\r\n",rs);

    time_wheel_handle(&wheel);

    sleep(2);
    time_wheel_handle(&wheel);


    return 0;
}