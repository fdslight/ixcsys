
#include<sys/types.h>
#include<libgen.h>
#include<string.h>
#include<unistd.h>
#include<sys/stat.h>

#include "listener.h"
#include "iscsid.h"

#include "../../../pywind/clib/debug.h"

/// 进程文件路径
static char pid_path[4096];
/// 运行目录
static char run_dir[4096];

/// 设置运行环境
static void ixc_set_run_env(char *argv[])
{
    strcpy(pid_path,"/tmp/ixcsys/iscsi/iscsid.pid");

    if(realpath(argv[0],run_dir)==NULL){
        STDERR("cannot get run path\r\n");
        exit(EXIT_FAILURE);
    }
    
    dirname(run_dir);
}

static void start(void)
{
    ixc_listener_init();
    ixc_listener_loop();
}

const char *ixc_iscsid_get_run_dir(void)
{
    return run_dir;
}

int main(int argc,char *argv[])
{
    const char *helper="start | stop | debug";
    pid_t pid;

    if(argc!=2){
        printf("%s\r\n",helper);
        return -1;
    }

    ixc_set_run_env(argv);

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