
#include<sys/types.h>

#include "listener.h"

#include "../../../pywind/clib/pycall.h"
#include "../../../pywind/clib/debug.h"

static void start(void)
{
    ixc_listener_init();
    ixc_listener_loop();
}

int main(int argc,char *argv[])
{
    const char *helper="start | stop | debug";
    pid_t pid;

    if(argc!=2){
        printf("%s\r\n",helper);
        return -1;
    }

    //ixc_set_run_env(argv);

    if(!strcmp(argv[1],"start")){
        pid=fork();
        if(pid!=0) exit(EXIT_SUCCESS);

        setsid();
        umask(0);

        pid=fork();
        if(pid!=0) exit(EXIT_SUCCESS);

        start();

        return 0;
    }

    if(!strcmp(argv[1],"stop")){
   
        return 0;
    }

    if(!strcmp(argv[1],"debug")){
        start();
        return 0;
    }

    printf("%s\r\n",helper);
    return -1;
}