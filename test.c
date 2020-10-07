#include<stdio.h>
#include<time.h>
#include<unistd.h>

#include "pywind/clib/timer.h"


struct time_wheel wheel;

void timeout_cb(void *data)
{
    printf("hello\r\n");
}

int main(int argc,char **argv[])
{
    int rs=time_wheel_new(&wheel,10,3,timeout_cb,1);
    time_wheel_add(&wheel,NULL,4);

    sleep(5);
    time_wheel_handle(&wheel);
    time_wheel_handle(&wheel);


    return 0;
}