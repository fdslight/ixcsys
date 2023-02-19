#define  PY_SSIZE_T_CLEAN
#include<Python.h>
#include<structmember.h>
#include<libgen.h>

#include "socket_server.h"

#include "../../../pywind/clib/pycall.h"
#include "../../../pywind/clib/debug.h"

/// 进程文件路径
static char pid_path[4096];
/// 运行目录
static char run_dir[4096];
/// RPC共享路径
static char rpc_path[4096];

/// 设置运行环境
static void ixc_set_run_env(char *argv[])
{
   
    strcpy(pid_path,"/tmp/ixcsys/netdog/netdog_core.pid");

    if(realpath(argv[0],run_dir)==NULL){
        STDERR("cannot get run path\r\n");
        exit(EXIT_FAILURE);
    }
    
    dirname(run_dir);

    strcpy(rpc_path,"/tmp/ixcsys/netdog/rpc.sock");
}

static void netdog_start(void)
{
    int rs=ixc_socket_server_init();
    if(rs<0){
        STDERR("cannot init socket server\r\n");
        exit(EXIT_SUCCESS);
    }
    ixc_socket_server_ioloop();
}

static void netdog_stop(void)
{
    
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

        netdog_start();

        return 0;
    }

    if(!strcmp(argv[1],"stop")){
        netdog_stop();
        return 0;
    }

    if(!strcmp(argv[1],"debug")){
        netdog_start();
        return 0;
    }

    printf("%s\r\n",helper);
    return -1;

    return 0;
}