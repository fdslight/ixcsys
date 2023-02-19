#define  PY_SSIZE_T_CLEAN
#include<Python.h>
#include<structmember.h>
#include<libgen.h>
#include<signal.h>
#include<execinfo.h>

#include "socket_server.h"

#include "../../../pywind/clib/pycall.h"
#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/pfile.h"

/// 进程文件路径
static char pid_path[4096];
/// 运行目录
static char run_dir[4096];

/// 设置运行环境
static void ixc_set_run_env(char *argv[])
{
   
    strcpy(pid_path,"/tmp/ixcsys/netdog/netdog_anylized.pid");

    if(realpath(argv[0],run_dir)==NULL){
        STDERR("cannot get run path\r\n");
        exit(EXIT_FAILURE);
    }
    
    dirname(run_dir);
}

static void ixc_segfault_info()
{
    void *bufs[4096];
    char **strs;
    int nptrs;

    nptrs=backtrace(bufs,4096);
    strs=backtrace_symbols(bufs,nptrs);
    if(NULL==strs) return;

    for(int n=0;n<nptrs;n++){
        fprintf(stderr,"%s\r\n",strs[n]);
    }
    free(strs);
    exit(EXIT_FAILURE);
}

static void netdog_stop(void)
{
    ixc_socket_server_uninit();
    exit(EXIT_SUCCESS);
}

static void ixc_signal_handle(int signum)
{
    switch(signum){
        case SIGINT:
            netdog_stop();
            break;
        case SIGSEGV:
            ixc_segfault_info();
            break;
    }
}

static void netdog_start(int is_debug)
{
    int rs;

    signal(SIGSEGV,ixc_signal_handle);
    signal(SIGINT,ixc_signal_handle);

    rs=ixc_socket_server_init();
    if(rs<0){
        STDERR("cannot init socket server\r\n");
        exit(EXIT_SUCCESS);
    }

    if(!is_debug) pfile_write(pid_path,getpid());
    ixc_socket_server_ioloop();
}

static void send_int_sig(void)
{
    pid_t pid=pfile_read(pid_path);
    if(pid<0) return;
    kill(pid,SIGINT);
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

        netdog_start(0);

        return 0;
    }

    if(!strcmp(argv[1],"stop")){
        send_int_sig();
        return 0;
    }

    if(!strcmp(argv[1],"debug")){
        netdog_start(1);
        return 0;
    }

    printf("%s\r\n",helper);
    return -1;

    return 0;
}