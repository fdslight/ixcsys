#include<unistd.h>
#include<signal.h>
#include<stdlib.h>
#include<execinfo.h>
#include<libgen.h>
#include<time.h>
#include<sys/wait.h>

#include<sched.h>
#include<arpa/inet.h>

#define  PY_SSIZE_T_CLEAN
#include<Python.h>

#include "session.h"
#include "tcp_listener.h"


#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/pfile.h"

/// 进程文件路径
static char pid_path[4096];
/// 运行目录
static char run_dir[4096];
/// 是否是监听实例
static int is_listener=0;
/// 是否是debug
static int is_debug=0;

static void ixc_listen_stop(void);
static void ixc_stop_children(void);

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
}

static void ixc_signal_handle(int signum)
{
    int _exit=1;
    switch(signum){
        case SIGINT:
            if(is_listener) {
                ixc_stop_children();
                ixc_tcp_listener_uninit();
            }
            else ixc_iscsi_session_delete();
            break;
        case SIGSEGV:
            ixc_segfault_info();
            break;
        case SIGCHLD:
            if(is_listener) {
                _exit=0;
                wait(NULL);
            }
            break;
    }

    if(!_exit) return;

    if(!access(pid_path,F_OK)) remove(pid_path);
    exit(EXIT_SUCCESS);
}

/// 设置运行环境
static void ixc_set_run_env(char *argv[])
{
    wchar_t *program = Py_DecodeLocale(argv[0], NULL);
    strcpy(pid_path,"/tmp/ixcsys/simpleNAS/iscsid.pid");

    if(realpath(argv[0],run_dir)==NULL){
        STDERR("cannot get run path\r\n");
        exit(EXIT_FAILURE);
    }
    
    dirname(run_dir);

    Py_SetProgramName(program);
}

static void ixc_listen_start(const char *addr,int debug)
{
    int is_ipv6=0,rs;
    unsigned char buf[256];
    
    is_debug=debug;

    rs=inet_pton(AF_INET6,addr,buf);
    if(rs<=0) rs=inet_pton(AF_INET,addr,buf);
    else is_ipv6=1;
    
    if(rs<1){
        STDERR("wrong ip address %s\r\n",addr);
        exit(EXIT_FAILURE);
    }

    if(!access(pid_path,F_OK)){
        STDERR("process exists\r\n");
        exit(EXIT_FAILURE);
    }

    signal(SIGSEGV,ixc_signal_handle);
    signal(SIGINT,ixc_signal_handle);
    signal(SIGCHLD,ixc_signal_handle);

    rs=ixc_tcp_listener_init(buf,is_ipv6);

    if(rs<0){
        STDERR("cannot listen tcp socket %s\r\n",addr);
        exit(EXIT_FAILURE);
    }

    is_listener=1;
    if(!debug) pfile_write(pid_path,getpid());

    ixc_tcp_listen();
}

// 停止子进程
static void ixc_stop_children(void)
{

}

static void ixc_listen_stop(void)
{
    pid_t pid=pfile_read(pid_path);

    if(pid<0) return;

    kill(pid,SIGINT);
}

char *ixc_iscsid_run_dir_get(void)
{
    return run_dir;
}

void ixc_iscsid_set_as_no_listener(void)
{
    is_listener=0;
}

int ixc_iscsid_is_debug(void)
{
    return is_debug;
}

void ixc_iscsid_set_pid_path(const char *path)
{
    strcpy(pid_path,path);
}

const char *ixc_iscsid_get_pid_path(void)
{
    return pid_path;
}

int main(int argc,char *argv[])
{
    const char *helper="ip4_or_ip6_address start | debug\r\nstop\r\n";
    pid_t pid;

    if(argc<2 || argc>3){
        printf("%s\r\n",helper);
        return -1;
    }

    if(argc==2 && strcmp(argv[1],"stop")){
        printf(helper);
        return -1;
    }

    if(argc==2 && !strcmp(argv[1],"stop")){
        ixc_listen_stop();
        return 0;
    }

    ixc_set_run_env(argv);

    if(!strcmp(argv[2],"start")){
        pid=fork();
        if(pid!=0) exit(EXIT_SUCCESS);

        setsid();
        umask(0);

        pid=fork();
        if(pid!=0) exit(EXIT_SUCCESS);

        ixc_listen_start(argv[1],0);

        return 0;
    }

    if(!strcmp(argv[2],"debug")){
        ixc_listen_start(argv[1],1);
        return 0;
    }

    printf("%s\r\n",helper);
    return -1;
}
